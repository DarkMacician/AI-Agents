from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

# Path to downloaded model
local_model_path = "codellama/CodeLlama-7b"

# Load tokenizer and model
tokenizer = AutoTokenizer.from_pretrained(local_model_path)
model = AutoModelForCausalLM.from_pretrained(local_model_path, torch_dtype=torch.float16, device_map="auto")

# Interactive loop
print("Code Generator is ready! Type your prompt (or 'exit' to stop):")
while True:
    prompt = input("\nYou: ")
    if prompt.lower() == "exit":
        print("Goodbye!")
        break

    # Tokenize and generate code
    inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
    output = model.generate(**inputs, max_new_tokens=200)

    # Decode and print result
    generated_code = tokenizer.decode(output[0], skip_special_tokens=True)
    print("\nGenerated Code:\n", generated_code)