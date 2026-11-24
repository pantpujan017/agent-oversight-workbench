
from pathlib import Path

from executor import WORKSPACE_ROOT, execute_file_action


print("\nTesting legitimate file operations...\n")

source = WORKSPACE_ROOT / "project" / "plan.txt"
destination = (
    WORKSPACE_ROOT / "review" / "security_validation_test.txt"
)

try:
    # Make sure this test does not overwrite an existing file.
    if destination.exists():
        raise ValueError(
            "Test destination already exists. Choose another filename."
        )

    result = execute_file_action(
        "copy_file",
        "project/plan.txt → review/security_validation_test.txt",
    )

    # Verify that the new file exists.
    if not destination.is_file():
        raise RuntimeError("The destination file was not created.")

    # Verify that the copied content matches the original.
    if source.read_bytes() != destination.read_bytes():
        raise RuntimeError("The copied file content does not match.")

    print("FUNCTIONAL TEST PASSED")
    print(result)
    print("\nSource file: project/plan.txt")
    print("Copied file: review/security_validation_test.txt")
    print("File contents match.")

except Exception as error:
    print("FUNCTIONAL TEST FAILED")
    print(error)
