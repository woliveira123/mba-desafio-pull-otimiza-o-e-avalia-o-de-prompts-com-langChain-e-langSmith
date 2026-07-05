"""
Script para fazer push de prompts otimizados ao LangSmith Prompt Hub.

Este script:
1. Lê os prompts otimizados de prompts/bug_to_user_story_v2.yml
2. Valida os prompts
3. Faz push PÚBLICO para o LangSmith Hub como {username}/bug_to_user_story_v2
4. Adiciona metadados (tags, descrição, técnicas utilizadas)
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from langsmith import Client
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from utils import load_yaml, check_env_vars, print_section_header

PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def validate_prompt(prompt_data: dict) -> tuple[bool, list]:
    """
    Valida estrutura básica de um prompt.

    Args:
        prompt_data: Dados do prompt (conteúdo da chave principal no YAML)

    Returns:
        (is_valid, errors) - Tupla com status e lista de erros
    """
    errors = []

    required_fields = ['description', 'system_prompt', 'version']
    for field in required_fields:
        if field not in prompt_data:
            errors.append(f"Campo obrigatório faltando: '{field}'")

    system_prompt = prompt_data.get('system_prompt', '').strip()
    if not system_prompt:
        errors.append("'system_prompt' está vazio")

    if '[TODO]' in system_prompt or 'TODO' in system_prompt:
        errors.append("'system_prompt' ainda contém marcadores TODO")

    techniques = prompt_data.get('techniques_applied', [])
    if len(techniques) < 2:
        errors.append(
            f"Mínimo de 2 técnicas obrigatórias em 'techniques_applied', "
            f"encontradas: {len(techniques)}"
        )

    return (len(errors) == 0, errors)


def push_prompt_to_langsmith(prompt_name: str, prompt_data: dict) -> bool:
    """
    Faz push do prompt otimizado para o LangSmith Hub (PÚBLICO).

    Args:
        prompt_name: Nome completo do prompt (ex: "username/bug_to_user_story_v2")
        prompt_data: Dados do prompt extraídos do YAML

    Returns:
        True se sucesso, False caso contrário
    """
    try:
        system_content = prompt_data.get('system_prompt', '')
        user_content = prompt_data.get('user_prompt', '{bug_report}')

        # Construir ChatPromptTemplate com system + human messages
        chat_prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(system_content),
            HumanMessagePromptTemplate.from_template(user_content),
        ])

        print(f"  Fazendo push para: {prompt_name}")

        # Push público ao LangSmith Hub
        client = Client()
        url = client.push_prompt(
            prompt_name,
            object=chat_prompt,
            is_public=True,
            description=prompt_data.get('description', '')
        )

        print(f"  ✓ Prompt publicado com sucesso!")
        print(f"  🔗 URL: {url}")
        return True

    except Exception as e:
        # 409 = prompt already up to date, treat as success
        if "409" in str(e) or "Nothing to commit" in str(e) or "LangSmithConflictError" in type(e).__name__:
            print(f"  ✓ Prompt ja esta publicado e atualizado no Hub (sem alteracoes desde o ultimo push)")
            return True
        import traceback
        print(f"  Erro ao fazer push:")
        print(f"  {type(e).__name__}: {e}")
        print(f"\n  Traceback completo:")
        traceback.print_exc()
        return False


def main():
    """Função principal"""
    print_section_header("PUSH DE PROMPTS OTIMIZADOS AO LANGSMITH HUB")

    required_vars = ["LANGSMITH_API_KEY", "USERNAME_LANGSMITH_HUB"]
    if not check_env_vars(required_vars):
        return 1

    username = os.getenv("USERNAME_LANGSMITH_HUB", "")

    yaml_path = PROJECT_ROOT / "prompts" / "bug_to_user_story_v2.yml"
    print(f"Carregando prompt de: {yaml_path}")

    data = load_yaml(yaml_path)
    if not data:
        print(f"\n❌ Não foi possível carregar o arquivo: {yaml_path}")
        print("Certifique-se de criar prompts/bug_to_user_story_v2.yml antes de fazer push.")
        return 1

    # Obter a chave principal do YAML (ex: "bug_to_user_story_v2")
    prompt_key = list(data.keys())[0]
    prompt_data = data[prompt_key]

    print(f"  ✓ Prompt carregado: {prompt_key}")

    # Validar estrutura do prompt
    print("\nValidando estrutura do prompt...")
    is_valid, errors = validate_prompt(prompt_data)

    if not is_valid:
        print("❌ Prompt inválido:")
        for error in errors:
            print(f"   - {error}")
        print("\nCorreja os erros acima e tente novamente.")
        return 1

    print("  ✓ Prompt válido!")

    # Exibir metadados
    techniques = prompt_data.get('techniques_applied', [])
    print(f"\nMétadados:")
    print(f"  Versão: {prompt_data.get('version', 'N/A')}")
    print(f"  Técnicas: {', '.join(techniques)}")
    print(f"  Tags: {', '.join(prompt_data.get('tags', []))}")

    # Nome do prompt no Hub
    prompt_name = f"{username}/bug_to_user_story_v2"

    print(f"\nPublicando prompt: {prompt_name}")
    success = push_prompt_to_langsmith(prompt_name, prompt_data)

    if success:
        print("\n✅ Push concluído com sucesso!")
        print("\nPróximos passos:")
        print("1. Verifique o prompt em: https://smith.langchain.com/hub")
        print("2. Execute a avaliação: python src/evaluate.py")
        return 0
    else:
        print("\n❌ Push falhou. Verifique as configurações e tente novamente.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
