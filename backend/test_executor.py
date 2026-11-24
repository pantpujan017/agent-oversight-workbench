
from executor import execute_file_action


print("\nTesting overwrite protection...\n")

try:
    execute_file_action(
        "copy_file",
        "project/plan.txt → review/plan.txt",
    )

    print("TEST FAILED: Existing file was overwritten.")

except ValueError as error:
    print("TEST PASSED")
    print(f"Overwrite prevented: {error}")
