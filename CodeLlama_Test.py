from transformers import AutoTokenizer, pipeline
import torch

# Model name (Make sure it's the correct one)
model_name = "codellama/CodeLlama-7b-hf"

# Load tokenizer and model pipeline
tokenizer = AutoTokenizer.from_pretrained(model_name, use_auth_token=True)
generator = pipeline(
    "text-generation",
    model=model_name,
    torch_dtype=torch.float16,
    device_map="auto",
)

print("CodeLlama Chatbot - Type 'exit' to stop")

while True:
    user_input = input("You: ")
    if user_input.lower() == "exit":
        print("Goodbye!")
        break

    sequences = generator(
        user_input,
        do_sample=True,
        top_k=10,
        temperature=0.1,
        top_p=0.95,
        num_return_sequences=1,
        eos_token_id=tokenizer.eos_token_id,
        max_length=200,
    )

    response = sequences[0]["generated_text"]
    print(f"Bot: {response.strip()}")