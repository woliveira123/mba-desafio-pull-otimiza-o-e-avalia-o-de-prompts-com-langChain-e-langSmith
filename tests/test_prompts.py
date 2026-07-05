"""
Testes automatizados para validação de prompts.
"""
import pytest
import yaml
import sys
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils import validate_prompt_structure


def load_prompts(file_path: str):
    """Carrega prompts do arquivo YAML."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


PROMPT_FILE = Path(__file__).parent.parent / "prompts" / "bug_to_user_story_v2.yml"


class TestPrompts:
    def test_prompt_has_system_prompt(self):
        """Verifica se o campo 'system_prompt' existe e não está vazio."""
        data = load_prompts(PROMPT_FILE)
        prompt_key = list(data.keys())[0]
        prompt = data[prompt_key]

        assert "system_prompt" in prompt, "Campo 'system_prompt' não encontrado no YAML"
        assert prompt["system_prompt"].strip(), "Campo 'system_prompt' está vazio"

    def test_prompt_has_role_definition(self):
        """Verifica se o prompt define uma persona (ex: 'Você é um Product Manager')."""
        data = load_prompts(PROMPT_FILE)
        prompt_key = list(data.keys())[0]
        system_prompt = data[prompt_key]["system_prompt"].lower()

        role_keywords = ["você é", "você é um", "you are", "sua especialidade", "sua função"]
        has_role = any(keyword in system_prompt for keyword in role_keywords)

        assert has_role, (
            "O system_prompt não define uma persona/role. "
            "Adicione uma definição como 'Você é um Product Manager Sênior...'"
        )

    def test_prompt_mentions_format(self):
        """Verifica se o prompt exige formato Markdown ou User Story padrão."""
        data = load_prompts(PROMPT_FILE)
        prompt_key = list(data.keys())[0]
        system_prompt = data[prompt_key]["system_prompt"].lower()

        format_keywords = [
            "como um", "eu quero", "para que",  # user story format
            "given", "when", "then",              # gherkin english
            "dado que", "quando", "então",        # gherkin portuguese
            "critérios de aceitação", "acceptance criteria",
            "user story", "formato"
        ]
        has_format = any(keyword in system_prompt for keyword in format_keywords)

        assert has_format, (
            "O prompt não menciona o formato esperado de User Story ou Markdown. "
            "Inclua instruções sobre o formato 'Como um... Eu quero... Para que...' "
            "e critérios de aceitação Given-When-Then."
        )

    def test_prompt_has_few_shot_examples(self):
        """Verifica se o prompt contém exemplos de entrada/saída (técnica Few-shot)."""
        data = load_prompts(PROMPT_FILE)
        prompt_key = list(data.keys())[0]
        system_prompt = data[prompt_key]["system_prompt"]

        # Verifica presença de exemplos (few-shot indicators)
        few_shot_indicators = [
            "exemplo", "example",
            "bug report:", "user story gerada:",
            "input:", "output:",
            "###", "---"
        ]
        system_lower = system_prompt.lower()
        has_examples = any(indicator in system_lower for indicator in few_shot_indicators)

        # Verifica se há pelo menos 2 ocorrências de marcadores de exemplo
        example_count = sum(
            system_lower.count(indicator)
            for indicator in ["exemplo", "example", "bug report:"]
        )

        assert has_examples and example_count >= 2, (
            "O prompt não contém exemplos de entrada/saída (Few-shot Learning). "
            "Adicione pelo menos 2 exemplos mostrando um Bug Report → User Story."
        )

    def test_prompt_no_todos(self):
        """Garante que você não esqueceu nenhum [TODO] no texto."""
        data = load_prompts(PROMPT_FILE)
        prompt_key = list(data.keys())[0]
        prompt = data[prompt_key]

        system_prompt = prompt.get("system_prompt", "")
        user_prompt = prompt.get("user_prompt", "")
        description = prompt.get("description", "")

        full_text = f"{system_prompt} {user_prompt} {description}"

        assert "[TODO]" not in full_text, (
            "O prompt contém marcadores [TODO] não resolvidos. "
            "Remova ou substitua todos os [TODO] antes de fazer push."
        )
        assert "TODO" not in full_text or "techniques_applied" in str(prompt), (
            "O prompt pode conter TODOs não resolvidos."
        )

    def test_minimum_techniques(self):
        """Verifica (através dos metadados do yaml) se pelo menos 2 técnicas foram listadas."""
        data = load_prompts(PROMPT_FILE)
        prompt_key = list(data.keys())[0]
        prompt = data[prompt_key]

        assert "techniques_applied" in prompt, (
            "Campo 'techniques_applied' não encontrado no YAML. "
            "Adicione uma lista com as técnicas de prompt engineering utilizadas."
        )

        techniques = prompt["techniques_applied"]
        assert isinstance(techniques, list), (
            "'techniques_applied' deve ser uma lista de strings."
        )
        assert len(techniques) >= 2, (
            f"Mínimo de 2 técnicas obrigatórias, encontradas: {len(techniques)}. "
            "Adicione pelo menos 2 técnicas em 'techniques_applied' no YAML."
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
