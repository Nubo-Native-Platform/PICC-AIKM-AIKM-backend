from typing import Any, Dict, List, Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)


class RedmineLoader:
    """Load issues from Redmine and convert them to text documents."""

    def __init__(self, url: str, api_key: str):
        try:
            from redminelib import Redmine
        except ImportError as exc:
            raise RuntimeError(
                "python-redmine is required for Redmine ingestion. "
                "Install the python-redmine package."
            ) from exc

        self.url = url.rstrip("/")
        self.redmine = Redmine(url, key=api_key)
        logger.info("Initialized Redmine client for %s", url)

    def load_issues(
        self,
        project_id: Optional[str] = None,
        status_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Load issues from Redmine."""
        try:
            filters: dict[str, Any] = {}
            if project_id:
                filters["project_id"] = project_id
            if status_id:
                filters["status_id"] = status_id
            if limit:
                filters["limit"] = limit

            issues = self.redmine.issue.filter(**filters)
            documents = [self._issue_to_document(issue) for issue in issues]
            logger.info("Loaded %d issues from Redmine", len(documents))
            return documents
        except Exception as exc:  # noqa: BLE001
            logger.error("Error loading Redmine issues: %s", exc)
            raise

    def _issue_to_document(self, issue: Any) -> Dict[str, Any]:
        content = f"Issue #{issue.id}: {issue.subject}\n\n"
        content += f"Status: {issue.status.name}\n"
        content += f"Priority: {issue.priority.name if hasattr(issue, 'priority') else 'N/A'}\n"
        content += f"Author: {issue.author.name}\n"
        content += f"Created: {issue.created_on}\n"
        content += f"Updated: {issue.updated_on}\n\n"

        if hasattr(issue, "description") and issue.description:
            content += f"Description:\n{issue.description}\n\n"

        if hasattr(issue, "custom_fields"):
            content += "Custom Fields:\n"
            for field in issue.custom_fields:
                content += f"  {field.name}: {field.value}\n"

        if hasattr(issue, "journals"):
            content += "\nComments:\n"
            for journal in issue.journals:
                if hasattr(journal, "notes") and journal.notes:
                    content += f"  - {journal.user.name} ({journal.created_on}): {journal.notes}\n"

        return {
            "content": content,
            "metadata": {
                "source": f"{self.url}/issues/{issue.id}",
                "type": "redmine_issue",
                "issue_id": issue.id,
                "project": issue.project.name if hasattr(issue, "project") else None,
                "status": issue.status.name,
                "created_on": str(issue.created_on),
                "updated_on": str(issue.updated_on),
            },
        }
