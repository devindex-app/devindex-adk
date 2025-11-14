import argparse
import asyncio
import os
import sys
from typing import List
from pathlib import Path
from dotenv import load_dotenv

from agent.agent import DevIndexAgent
from google.adk.runners import InMemoryRunner
from google.genai import types

# Load environment variables from .env file in project root
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Initialize database logger early to ensure logs directory is created
try:
    from database.logger import get_db_logger
    db_logger = get_db_logger("main")
    db_logger.info("=" * 60)
    db_logger.info("DevIndex Agent Starting")
    db_logger.info("=" * 60)
    
    # Verify logs directory exists
    logs_dir = Path(__file__).parent.parent / "logs"
    if logs_dir.exists():
        db_logger.info(f"✓ Logs directory exists: {logs_dir}")
    else:
        db_logger.warning(f"⚠ Logs directory not found: {logs_dir}")
        
    # Check database setup
    if os.environ.get("DATABASE_URL"):
        db_logger.info("✓ DATABASE_URL is set")
        try:
            from database.db import DatabaseManager
            db_logger.info("✓ Database module imported successfully")
            # Test database connection (just check if it initializes)
            try:
                db_manager = DatabaseManager()
                db_logger.info("✓ Database manager initialized successfully")
            except Exception as db_init_error:
                db_logger.error(f"❌ Database manager initialization failed: {db_init_error}", exc_info=True)
        except ImportError as import_error:
            db_logger.error(f"❌ Failed to import database module: {import_error}", exc_info=True)
    else:
        db_logger.warning("⚠ DATABASE_URL not set - database operations will be skipped")
        
except Exception as logger_error:
    print(f"⚠ Warning: Could not initialize database logger: {logger_error}")
    import traceback
    traceback.print_exc()


def raise_if_env_absent(required_api_keys: List[str]):
    """
    Check for required environment variables.

    Args:
        required_api_keys: List of required environment variable names (e.g., ['ANTHROPIC_API_KEY', 'GOOGLE_API_KEY'])
    """
    errors = []

    for api_key in required_api_keys:
        if os.environ.get(api_key, None) is None:
            errors.append(f"❌ {api_key} is not set")

    if len(errors) > 0:
        raise ValueError("The following checks failed:\n" + "\n".join(errors))

async def main():
    raise_if_env_absent(["GOOGLE_API_KEY"])
    
    # Log startup
    try:
        from database.logger import get_db_logger
        db_logger = get_db_logger("main")
        db_logger.info("Starting agent main function")
    except Exception:
        pass  # Logger already initialized above, or failed

    parser = argparse.ArgumentParser(description="DevIndex Agent - Analyze GitHub user skills from a repository")
    parser.add_argument("--username", required=True, help="GitHub username to analyze")
    parser.add_argument("--repo", required=True, help="Repository to analyze (e.g., 'owner/repo' or 'repo' if owned by user)")
    args = parser.parse_args()
    
    # Log arguments
    try:
        from database.logger import get_db_logger
        db_logger = get_db_logger("main")
        db_logger.info(f"Arguments - Username: {args.username}, Repo: {args.repo}")
    except Exception:
        pass

    session_state = {
        "username": args.username,
        "repo": args.repo,
    }

    runner = InMemoryRunner(
        app_name="devindex_agent",
        agent=DevIndexAgent(name="devindex_agent"),
    )

    session = await runner.session_service.create_session(
        app_name="devindex_agent", user_id="1234", state=session_state
    )

    # Log that we're starting the agent
    try:
        from database.logger import get_db_logger
        db_logger = get_db_logger("main")
        db_logger.info("Starting agent execution...")
    except Exception:
        pass
    
    # Run the agent
    event_count = 0
    try:
        async for event in runner.run_async(
            user_id="1234",
            session_id=session.id,
            new_message=types.Content(role="user", parts=[types.Part(text="Follow the system instruction.")]),
        ):
            event_count += 1
            print(event.model_dump_json(exclude_unset=True, exclude_defaults=True, exclude_none=True))
    except Exception as agent_error:
        try:
            from database.logger import get_db_logger
            db_logger = get_db_logger("main")
            db_logger.error(f"Agent execution failed: {agent_error}", exc_info=True)
        except Exception:
            pass
        raise
    
    # Log completion
    try:
        from database.logger import get_db_logger
        db_logger = get_db_logger("main")
        db_logger.info(f"Agent execution completed - processed {event_count} events")
    except Exception:
        pass
    
    # After all events are processed, display the skill vector if available
    updated_session = await runner.session_service.get_session(app_name="devindex_agent", user_id="1234", session_id=session.id)
    
    # Log session retrieval
    try:
        from database.logger import get_db_logger
        db_logger = get_db_logger("main")
        if updated_session:
            db_logger.info("Session retrieved successfully")
        else:
            db_logger.error("Failed to retrieve updated session")
    except Exception:
        pass
    
    # Log session state for debugging
    try:
        from database.logger import get_db_logger
        db_logger = get_db_logger("main")
        db_logger.info("Agent execution completed, checking session state...")
        db_logger.debug(f"Session state keys: {list(updated_session.state.keys()) if updated_session else 'No session'}")
    except Exception:
        pass
    
    # Check for skill_vector in session state (this is what the agent actually stores)
    skill_vector_data = updated_session.state.get("skill_vector") if updated_session else None
    
    # Log what we found
    try:
        from database.logger import get_db_logger
        db_logger = get_db_logger("main")
        if skill_vector_data:
            db_logger.info(f"✓ Found skill_vector_data in session state")
            db_logger.debug(f"skill_vector_data type: {type(skill_vector_data)}")
            if isinstance(skill_vector_data, dict):
                db_logger.debug(f"skill_vector_data keys: {list(skill_vector_data.keys())}")
                if "skills" in skill_vector_data:
                    db_logger.debug(f"skills list length: {len(skill_vector_data.get('skills', []))}")
        else:
            db_logger.warning("skill_vector_data is None - cannot extract skills")
    except Exception:
        pass
    
    if skill_vector_data:
        # Extract skills from the structured skill_vector
        try:
            from database.logger import get_db_logger
            db_logger = get_db_logger("main")
            db_logger.debug(f"Extracting skills from skill_vector_data...")
        except Exception:
            pass
        
        skills_list = skill_vector_data.get("skills", []) if isinstance(skill_vector_data, dict) else []
        
        # Log the extraction process
        try:
            from database.logger import get_db_logger
            db_logger = get_db_logger("main")
            db_logger.debug(f"skills_list type: {type(skills_list)}, length: {len(skills_list) if isinstance(skills_list, list) else 'N/A'}")
            if skills_list:
                db_logger.debug(f"First skill item: {skills_list[0] if len(skills_list) > 0 else 'N/A'}")
        except Exception:
            pass
        
        skill_vector_dict = {}
        for skill in skills_list:
            if isinstance(skill, dict) and "name" in skill and "score" in skill:
                skill_vector_dict[skill["name"]] = skill["score"]
            elif isinstance(skill, dict):
                # Log unexpected structure
                try:
                    from database.logger import get_db_logger
                    db_logger = get_db_logger("main")
                    db_logger.warning(f"Skill item has unexpected structure: {skill}")
                except Exception:
                    pass
        
        # Generate output for display
        if skill_vector_dict:
            formatted_skills = [f"  {name}: {score}" for name, score in sorted(skill_vector_dict.items(), key=lambda x: x[1], reverse=True)]
            username = skill_vector_data.get("username", args.username) if isinstance(skill_vector_data, dict) else args.username
            output = f"""
Skill Vector for {username} (Repository: {args.repo}):
{chr(10).join(formatted_skills) if formatted_skills else '  No skills identified'}
            """.strip()
            
            print("\n" + "="*60)
            print(output)
            print("="*60)
        else:
            print("\n⚠ Skill vector found but no skills extracted")
            try:
                from database.logger import get_db_logger
                db_logger = get_db_logger("main")
                db_logger.warning(f"skill_vector_data structure: {type(skill_vector_data)}")
                db_logger.debug(f"skill_vector_data: {skill_vector_data}")
            except Exception:
                pass
        
        # Log whether skill_vector_dict exists and attempt to save
        try:
            from database.logger import get_db_logger
            db_logger = get_db_logger("main")
            if skill_vector_dict:
                db_logger.info(f"✓ Extracted skill_vector_dict with {len(skill_vector_dict)} skills")
                db_logger.debug(f"Skill vector dict: {skill_vector_dict}")
            else:
                db_logger.warning("⚠ Failed to extract skills from skill_vector_data")
                db_logger.debug(f"skill_vector_data type: {type(skill_vector_data)}, content: {skill_vector_data}")
        except Exception:
            pass
        
        # Save to database if we have skills
        if skill_vector_dict:
            # Log that we're attempting to save
            try:
                from database.logger import get_db_logger
                db_logger = get_db_logger("main")
                db_logger.info("=" * 60)
                db_logger.info("Attempting to save skill vector to database")
                db_logger.info(f"Username: {args.username}, Repo: {args.repo}")
                db_logger.info(f"Skills count: {len(skill_vector_dict)}")
            except Exception:
                pass
            
            print(f"\n{'='*60}")
            print(f"📊 Skill Vector Summary:")
            print(f"   Total skills: {len(skill_vector_dict)}")
            print(f"   Skills: {', '.join(list(skill_vector_dict.keys())[:5])}{'...' if len(skill_vector_dict) > 5 else ''}")
            print(f"{'='*60}\n")
            
            # Verify logs directory exists before saving
            logs_dir = Path(__file__).parent.parent / "logs"
            if not logs_dir.exists():
                print(f"⚠ Creating logs directory: {logs_dir}")
                logs_dir.mkdir(exist_ok=True)
                print(f"✓ Logs directory created")
            
            try:
                # Import and verify database modules are available
                print("📦 Verifying database modules...")
                from utils.db_utils import save_skill_vector_to_db
                from database.logger import get_db_logger
                from database.db import DatabaseManager
                print("✓ All database modules imported successfully")
                
                # Verify logger is working
                test_logger = get_db_logger("main")
                test_logger.info("About to save skill vector to database")
                print(f"✓ Database logger is working (check logs/database_*.log)")
                
                # Save to database
                print(f"\n💾 Saving to database...")
                saved = save_skill_vector_to_db(
                    username=args.username,
                    repo_name=args.repo,
                    skills=skill_vector_dict
                )
                if saved:
                    print(f"\n✓ Skill vector saved to database successfully!")
                    test_logger.info("Skill vector save completed successfully")
                else:
                    if os.environ.get("DATABASE_URL"):
                        print(f"\n⚠ Database save failed - check logs/database_*.log for details")
                        test_logger.warning("Database save returned False")
                    else:
                        print(f"\n⚠ DATABASE_URL not set - skipping database save")
                        test_logger.warning("DATABASE_URL not set, save skipped")
            except ImportError as e:
                print(f"\n❌ Database module import failed: {e}")
                try:
                    from database.logger import get_db_logger
                    error_logger = get_db_logger("main")
                    error_logger.error(f"Database module import failed: {e}", exc_info=True)
                except Exception:
                    pass
                import traceback
                traceback.print_exc()
            except Exception as e:
                print(f"\n❌ Unexpected error saving to database: {e}")
                print(f"   Check logs/database_*.log for full error details")
                import traceback
                traceback.print_exc()
                # Try to log the error
                try:
                    from database.logger import get_db_logger
                    error_logger = get_db_logger("main")
                    error_logger.error(f"Unexpected error in main: {e}", exc_info=True)
                except Exception:
                    pass
        else:
            # Log that skill_vector_dict is missing
            try:
                from database.logger import get_db_logger
                db_logger = get_db_logger("main")
                db_logger.warning("skill_vector_dict is None or empty - cannot save to database")
                db_logger.debug(f"Session state keys available: {list(updated_session.state.keys()) if updated_session else 'No session'}")
            except Exception:
                pass
            print(f"\n⚠ No skill_vector_dict found - cannot save to database")
    
    else:
        # Log if skill_vector_output is missing
        try:
            from database.logger import get_db_logger
            db_logger = get_db_logger("main")
            if not updated_session:
                db_logger.error("No updated session found after agent execution")
            elif "skill_vector_output" not in updated_session.state:
                db_logger.warning("skill_vector_output not found in session state")
                db_logger.debug(f"Available keys: {list(updated_session.state.keys())}")
        except Exception:
            pass
        print(f"\n⚠ No skill_vector_output found in session state")


if __name__ == "__main__":
    asyncio.run(main())
