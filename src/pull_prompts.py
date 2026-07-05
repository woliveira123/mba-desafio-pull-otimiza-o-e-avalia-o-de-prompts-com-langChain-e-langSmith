"""
Script para fazer pull de prompts do LangSmith Prompt Hub.

Este script:
1. Conecta ao LangSmith usando credenciais do .env
2. Faz pull do prompt leonanluppi/bug_to_user_story_v1 do Hub
3. Salva localmente em prompts/bug_to_user_story_v1.yml
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from langsmith import Client
from utils import save_yaml, check_env_vars, print_section_header

PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def pull_prompts_from_langsmith():
    """
    Faz pull do prompt de baixa qualidade do LangSmith Hub
    e salva localmente em formato YAML.
    """
    print("Conectando ao LangSmith Hub...")

    prompt_name = "leonanluppi/bug_to_user_story_v1"

    try:
        print(f"  Fazendo pull de: {prompt_name}")
        client = Client()
        prompt = client.pull_prompt(prompt_name, dangerously_pull_public_prompt=True)
        print(f"  ✓ Prompt carregado com sucesso")

        # Extrair mensagens do ChatPromptTemplate
        messages = prompt.messages

        system_content = ""
        user_content = ""

        for msg in messages:
            role = msg.__class__.__name__.lower()
            if "system" in role:
                system_content = msg.prompt.template if hasattr(msg, 'prompt') else str(msg)
            elif "human" in role:
                user_content = msg.prompt.template if hasattr(msg, 'prompt') else str(msg)

        prompt_data = {
            "bug_to_user_story_v1": {
                "description": "Prompt para converter relatos de bugs em User Stories",
                "system_prompt": system_content,
                "user_prompt": user_content,
                "version": "v1",
                "created_at": "2025-01-15",
                "tags": ["bug-analysis", "user-story", "product-management"],
                "source": f"https://smith.langchain.com/hub/{prompt_name}"
            }
        }

        output_path = str(PROJECT_ROOT / "prompts" / "bug_to_user_story_v1.yml")

        if save_yaml(prompt_data, output_path):
            print(f"  ✓ Prompt salvo em: {output_path}")
            return True
        else:
            print(f"  ❌ Erro ao salvar prompt")
            return False

    except Exception as e:
        print(f"  ❌ Erro ao fazer pull do prompt: {e}")
        print(f"\n  Verifique:")
        print(f"  - LANGSMITH_API_KEY está configurada no .env")
        print(f"  - O prompt '{prompt_name}' existe no LangSmith Hub")
        return False


def main():
    """Função principal"""
    print_section_header("PULL DE PROMPTS DO LANGSMITH HUB")

    required_vars = ["LANGSMITH_API_KEY"]
    if not check_env_vars(required_vars):
        return 1

    success = pull_prompts_from_langsmith()

    if success:
        print("\n✅ Pull concluído com sucesso!")
        print("\nPróximos passos:")
        print("1. Analise o prompt em prompts/bug_to_user_story_v1.yml")
        print("2. Crie sua versão otimizada em prompts/bug_to_user_story_v2.yml")
        print("3. Faça push: python src/push_prompts.py")
        return 0
    else:
        print("\n❌ Pull falhou. Verifique as configurações e tente novamente.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
