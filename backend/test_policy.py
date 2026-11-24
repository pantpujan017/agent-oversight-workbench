
from policy import evaluate_action


print("\nTESTING POLICY ENGINE")
print("=====================\n")


tests = [
    (
        "Valid file copy",
        "copy_file",
        "project/plan.txt",
        "review/policy_test_copy.txt",
        True,
    ),
    (
        "External destination",
        "copy_file",
        "project/plan.txt",
        "../outside.txt",
        False,
    ),
    (
        "Existing destination",
        "copy_file",
        "project/plan.txt",
        "review/plan.txt",
        False,
    ),
    (
        "Nonexistent source",
        "copy_file",
        "missing.txt",
        "review/missing.txt",
        False,
    ),
    (
        "Unsupported operation",
        "delete_file",
        "project/plan.txt",
        "review/plan.txt",
        False,
    ),
]


passed = 0

for name, tool, source, destination, expected in tests:

    result = evaluate_action(
        tool,
        source,
        destination,
    )

    success = result.allowed == expected

    if success:
        passed += 1
        print(f"PASSED: {name}")
    else:
        print(f"FAILED: {name}")
        print(f"Reason: {result.reason}")


print(f"\nRESULT: {passed}/{len(tests)} tests passed.")
