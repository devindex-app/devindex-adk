# GitHub Developer Scorer Agent

This agent scores a developer's contributions on GitHub based on their pull requests and recent commits to personal projects.

## CLI Interface

To run the agent, use the following command:

```bash
python -m agent.main --developer_username <GITHUB_USERNAME>
```

### Arguments

- `--developer_username`: **(required)** The GitHub username of the developer to be scored.

## Agent Behavior

The agent performs the following steps:

1.  **Fetches Pull Requests:** It uses the `gh` command-line tool to fetch the last 5 pull requests for the specified developer.
2.  **Fetches Recent Commits:** It uses the `gh` and `git` command-line tools to fetch the last year of commits from the developer's personal repositories.
3.  **Analyzes Contributions:** It uses a large language model to analyze the titles and bodies of the pull requests, and the recent commit history of the personal projects, paying special attention to commit quality (clear messages, atomic commits).
4.  **Scores Developer:** Based on the analysis, it assigns a score to the developer on a scale of 1 to 100.
5.  **Provides Reasoning:** It provides a brief reasoning for the score given.