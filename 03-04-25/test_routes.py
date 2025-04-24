import requests

base_url = "http://localhost:5000"

# Teste da página inicial
print("Testando página inicial...")
response = requests.get(f"{base_url}/")
print(f"Status: {response.status_code}")
print(f"Tem link para login: {'login' in response.text}")

# Teste da página de login
print("\nTestando página de login...")
response = requests.get(f"{base_url}/login")
print(f"Status: {response.status_code}")
print(f"Tem formulário de login: {'name=\"email\"' in response.text}")
print(f"Tem formulário de senha: {'name=\"senha\"' in response.text}")

print("\nVerificação concluída. Execute a aplicação e navegue para http://localhost:5000/login")