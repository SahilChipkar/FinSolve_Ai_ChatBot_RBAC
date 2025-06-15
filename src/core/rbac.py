# src/core/rbac.py

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# Define all possible departments for strict control
ALL_DEPARTMENTS = ["finance", "marketing", "hr", "engineering", "general"]

# Define role-based access control permissions
# Each role maps to a dictionary of filters for ChromaDB metadata.
# 'department': allows access to documents with this specific department.
# '$or': allows access to documents matching any of the conditions within the list.
# 'access_level': could be used for finer-grained control within a department (not fully implemented here yet).

ROLE_PERMISSIONS: Dict[str, Dict[str, Any]] = {
    "Finance Team": {
        "department": "finance"
    },
    "Marketing Team": {
        "department": "marketing" # CORRECTED: Ensure Marketing Team has access to 'marketing' department
    },
    "HR Team": {
        "department": "hr"
    },
    "Engineering Department": {
        "department": "engineering"
    },
    "C-Level Executives": {
        # C-Level has full access to all departments
        "$or": [{"department": dept} for dept in ALL_DEPARTMENTS]
    },
    "Employee Level": {
        "department": "general" # General company info, policies, events
    },
    "Admin": {
        # Admin has absolute full access, similar to C-Level
        "$or": [{"department": dept} for dept in ALL_DEPARTMENTS]
    }
}

def get_chroma_filter_for_role(role: str) -> Dict[str, Any]:
    """
    Returns the ChromaDB metadata filter dictionary for a given role.
    If a role is not found, or has no specific department permissions,
    it returns an empty dictionary, which means no metadata filtering will be applied
    by ChromaDB on the department field. The calling RAG chain needs to handle
    the interpretation of an empty filter (e.g., restricted access by default).
    """
    permissions = ROLE_PERMISSIONS.get(role)
    if permissions:
        logger.debug(f"Permissions for role '{role}': {permissions}")
        # ChromaDB expects a dictionary for the 'where' clause.
        # If the permission is already a "$or" or specific department, return it directly.
        if "department" in permissions or "$or" in permissions:
            return permissions
        else:
            # If the permission structure is valid but doesn't contain department/or (e.g. empty for now)
            return {}
    else:
        logger.warning(f"Role '{role}' not found in ROLE_PERMISSIONS. Returning empty filter.")
        return {} # No specific filter for unknown roles, let RAGChain deny by default.

# Example usage (for testing)
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    print("--- Testing get_chroma_filter_for_role ---")

    roles_to_test = ["Finance Team", "Marketing Team", "HR Team", "Engineering Department", "C-Level Executives", "Employee Level", "Admin", "Unknown Role"]

    for role in roles_to_test:
        filter_dict = get_chroma_filter_for_role(role)
        print(f"Role: '{role}' -> Filter: {filter_dict}")

