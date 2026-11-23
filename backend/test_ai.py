
from ai_service import generate_action_proposal


instruction = "Copy the project plan into the archive folder."

print("\nSending instruction to Gemini...\n")

try:
    proposal = generate_action_proposal(instruction)

    print("AI GENERATED PROPOSAL")
    print("---------------------")
    print(proposal.model_dump_json(indent=2))

except Exception as error:
    print("AI TEST FAILED")
    print(error)
