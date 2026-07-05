"""
Módulo de métricas customizadas para avaliação de prompts.

Este módulo implementa métricas gerais e específicas para Bug to User Story:

MÉTRICAS GERAIS (3):
1. F1-Score: Balanceamento entre Precision e Recall
2. Clarity: Clareza e estrutura da resposta
3. Precision: Informações corretas e relevantes

MÉTRICAS ESPECÍFICAS PARA BUG TO USER STORY (4):
4. Tone Score: Tom profissional e empático
5. Acceptance Criteria Score: Qualidade dos critérios de aceitação
6. User Story Format Score: Formato correto (Como... Eu quero... Para que...)
7. Completeness Score: Completude e contexto técnico

Suporta múltiplos providers de LLM:
- OpenAI (gpt-4o, gpt-4o-mini)
- Google Gemini (gemini-2.5-flash)

Configure o provider no arquivo .env através da variável LLM_PROVIDER.
"""

import os
import json
import re
from typing import Dict, Any
from dotenv import load_dotenv
from langchain_core.messages import SystemMessage, HumanMessage
from utils import get_eval_llm

load_dotenv()


def get_evaluator_llm():
    """
    Retorna o LLM configurado para avaliação.
    Suporta OpenAI e Google Gemini baseado no .env
    """
    return get_eval_llm(temperature=0)


def extract_json_from_response(response_text: str) -> Dict[str, Any]:
    """
    Extrai JSON de uma resposta de LLM que pode conter texto adicional.
    """
    try:
        # Tentar parsear diretamente
        return json.loads(response_text)
    except json.JSONDecodeError:
        # Tentar encontrar JSON no meio do texto
        start = response_text.find('{')
        end = response_text.rfind('}') + 1

        if start != -1 and end > start:
            try:
                json_str = response_text[start:end]
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

        # Se não conseguir extrair, retornar valores default
        print(f"⚠️  Não foi possível extrair JSON da resposta: {response_text[:200]}...")
        return {"score": 0.0, "reasoning": "Erro ao processar resposta"}


def evaluate_f1_score(question: str, answer: str, reference: str) -> Dict[str, Any]:
    """
    Calcula F1-Score usando LLM-as-Judge.

    F1-Score = 2 * (Precision * Recall) / (Precision + Recall)

    Args:
        question: Pergunta feita pelo usuário
        answer: Resposta gerada pelo prompt
        reference: Resposta esperada (ground truth)

    Returns:
        Dict com score e reasoning
    """
    evaluator_prompt = f"""
Você é um avaliador especializado em medir a qualidade de respostas geradas por IA.

Sua tarefa é calcular PRECISION e RECALL para determinar o F1-Score.

PERGUNTA DO USUÁRIO:
{question}

RESPOSTA ESPERADA (Ground Truth):
{reference}

RESPOSTA GERADA PELO MODELO:
{answer}

INSTRUÇÕES:

1. PRECISION (0.0 a 1.0):
   - Quantas informações na resposta gerada são CORRETAS e RELEVANTES?
   - Penalizar informações incorretas, inventadas ou desnecessárias
   - 1.0 = todas informações são corretas e relevantes
   - 0.0 = nenhuma informação é correta ou relevante

2. RECALL (0.0 a 1.0):
   - Quantas informações da resposta esperada estão PRESENTES na resposta gerada?
   - Penalizar informações importantes que foram omitidas
   - 1.0 = todas informações importantes estão presentes
   - 0.0 = nenhuma informação importante está presente

3. RACIOCÍNIO:
   - Explique brevemente sua avaliação
   - Cite exemplos específicos do que estava correto/incorreto

IMPORTANTE: Retorne APENAS um objeto JSON válido no formato:
{{
  "precision": <valor entre 0.0 e 1.0>,
  "recall": <valor entre 0.0 e 1.0>,
  "reasoning": "<sua explicação em até 100 palavras>"
}}

NÃO adicione nenhum texto antes ou depois do JSON.
"""

    try:
        llm = get_evaluator_llm()
        response = llm.invoke([HumanMessage(content=evaluator_prompt)])
        result = extract_json_from_response(response.content)

        precision = float(result.get("precision", 0.0))
        recall = float(result.get("recall", 0.0))

        # Calcular F1-Score
        if (precision + recall) > 0:
            f1_score = 2 * (precision * recall) / (precision + recall)
        else:
            f1_score = 0.0

        return {
            "score": round(f1_score, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "reasoning": result.get("reasoning", "")
        }

    except Exception as e:
        print(f"❌ Erro ao avaliar F1-Score: {e}")
        return {
            "score": 0.0,
            "precision": 0.0,
            "recall": 0.0,
            "reasoning": f"Erro na avaliação: {str(e)}"
        }


def evaluate_clarity(question: str, answer: str, reference: str) -> Dict[str, Any]:
    """
    Avalia a clareza e estrutura da resposta usando LLM-as-Judge.

    Args:
        question: Pergunta feita pelo usuário
        answer: Resposta gerada pelo prompt
        reference: Resposta esperada (ground truth)

    Returns:
        Dict com score e reasoning
    """
    evaluator_prompt = f"""
Você é um avaliador especializado em medir a CLAREZA de respostas geradas por IA.

PERGUNTA DO USUÁRIO:
{question}

RESPOSTA GERADA PELO MODELO:
{answer}

RESPOSTA ESPERADA (Referência):
{reference}

INSTRUÇÕES:

Avalie a CLAREZA da resposta gerada com base nos critérios:

1. ORGANIZAÇÃO (0.0 a 1.0):
   - A resposta tem estrutura lógica e bem organizada?
   - Informações estão em ordem sensata?

2. LINGUAGEM (0.0 a 1.0):
   - Usa linguagem simples e direta?
   - Evita jargões desnecessários?
   - Fácil de entender?

3. AUSÊNCIA DE AMBIGUIDADE (0.0 a 1.0):
   - A resposta é clara e sem ambiguidades?
   - Não deixa dúvidas sobre o que está sendo comunicado?

4. CONCISÃO (0.0 a 1.0):
   - É concisa sem ser curta demais?
   - Não tem informações redundantes?

Calcule a MÉDIA dos 4 critérios para obter o score final.

IMPORTANTE: Retorne APENAS um objeto JSON válido no formato:
{{
  "score": <valor entre 0.0 e 1.0>,
  "reasoning": "<explicação detalhada da avaliação em até 100 palavras>"
}}

NÃO adicione nenhum texto antes ou depois do JSON.
"""

    try:
        llm = get_evaluator_llm()
        response = llm.invoke([HumanMessage(content=evaluator_prompt)])
        result = extract_json_from_response(response.content)

        score = float(result.get("score", 0.0))

        return {
            "score": round(score, 4),
            "reasoning": result.get("reasoning", "")
        }

    except Exception as e:
        print(f"❌ Erro ao avaliar Clarity: {e}")
        return {
            "score": 0.0,
            "reasoning": f"Erro na avaliação: {str(e)}"
        }


def evaluate_precision(question: str, answer: str, reference: str) -> Dict[str, Any]:
    """
    Avalia a precisão da resposta usando LLM-as-Judge.

    Args:
        question: Pergunta feita pelo usuário
        answer: Resposta gerada pelo prompt
        reference: Resposta esperada (ground truth)

    Returns:
        Dict com score e reasoning
    """
    evaluator_prompt = f"""
Você é um avaliador especializado em detectar PRECISÃO e ALUCINAÇÕES em respostas de IA.

PERGUNTA DO USUÁRIO:
{question}

RESPOSTA GERADA PELO MODELO:
{answer}

RESPOSTA ESPERADA (Ground Truth):
{reference}

INSTRUÇÕES:

Avalie a PRECISÃO da resposta gerada:

1. AUSÊNCIA DE ALUCINAÇÕES (0.0 a 1.0):
   - A resposta contém informações INVENTADAS ou não verificáveis?
   - Todas as afirmações são baseadas em fatos?
   - 1.0 = nenhuma alucinação detectada
   - 0.0 = resposta cheia de informações inventadas

2. FOCO NA PERGUNTA (0.0 a 1.0):
   - A resposta responde EXATAMENTE o que foi perguntado?
   - Não divaga ou adiciona informações não solicitadas?
   - 1.0 = totalmente focada
   - 0.0 = completamente fora do tópico

3. CORREÇÃO FACTUAL (0.0 a 1.0):
   - As informações estão CORRETAS quando comparadas com a referência?
   - Não há erros ou imprecisões?
   - 1.0 = todas informações corretas
   - 0.0 = informações incorretas

Calcule a MÉDIA dos 3 critérios para obter o score final.

IMPORTANTE: Retorne APENAS um objeto JSON válido no formato:
{{
  "score": <valor entre 0.0 e 1.0>,
  "reasoning": "<explicação detalhada em até 100 palavras, cite exemplos>"
}}

NÃO adicione nenhum texto antes ou depois do JSON.
"""

    try:
        llm = get_evaluator_llm()
        response = llm.invoke([HumanMessage(content=evaluator_prompt)])
        result = extract_json_from_response(response.content)

        score = float(result.get("score", 0.0))

        return {
            "score": round(score, 4),
            "reasoning": result.get("reasoning", "")
        }

    except Exception as e:
        print(f"❌ Erro ao avaliar Precision: {e}")
        return {
            "score": 0.0,
            "reasoning": f"Erro na avaliação: {str(e)}"
        }


def evaluate_tone_score(bug_report: str, user_story: str, reference: str) -> Dict[str, Any]:
    """
    Avalia o tom da user story (profissional e empático).
    """
    evaluator_prompt = f"""
Você é um avaliador especializado em User Stories ágeis.

BUG REPORT ORIGINAL:
{bug_report}

USER STORY GERADA:
{user_story}

USER STORY ESPERADA (Referência):
{reference}

INSTRUÇÕES:

Avalie o TOM da user story gerada com base nos critérios:

1. PROFISSIONALISMO (0.0 a 1.0)
2. EMPATIA COM USUÁRIO (0.0 a 1.0)
3. FOCO EM VALOR (0.0 a 1.0)
4. LINGUAGEM POSITIVA (0.0 a 1.0)

Calcule a MÉDIA dos 4 critérios para obter o score final.

IMPORTANTE: Retorne APENAS um objeto JSON válido no formato:
{{
  "score": <valor entre 0.0 e 1.0>,
  "reasoning": "<explicação detalhada em até 150 palavras>"
}}

NÃO adicione nenhum texto antes ou depois do JSON.
"""

    try:
        llm = get_evaluator_llm()
        response = llm.invoke([HumanMessage(content=evaluator_prompt)])
        result = extract_json_from_response(response.content)

        score = float(result.get("score", 0.0))

        return {
            "score": round(score, 4),
            "reasoning": result.get("reasoning", "")
        }

    except Exception as e:
        print(f"❌ Erro ao avaliar Tone Score: {e}")
        return {
            "score": 0.0,
            "reasoning": f"Erro na avaliação: {str(e)}"
        }


def evaluate_acceptance_criteria_score(bug_report: str, user_story: str, reference: str) -> Dict[str, Any]:
    """
    Avalia a qualidade dos critérios de aceitação.
    """
    evaluator_prompt = f"""
Você é um avaliador especializado em Critérios de Aceitação de User Stories.

BUG REPORT ORIGINAL:
{bug_report}

USER STORY GERADA:
{user_story}

USER STORY ESPERADA (Referência):
{reference}

INSTRUÇÕES:

Avalie os CRITÉRIOS DE ACEITAÇÃO da user story gerada:

1. FORMATO ESTRUTURADO (0.0 a 1.0) - Usa Given-When-Then?
2. ESPECIFICIDADE E TESTABILIDADE (0.0 a 1.0) - São mensuráveis?
3. QUANTIDADE ADEQUADA (0.0 a 1.0) - Ideal: 3-7 critérios
4. COBERTURA COMPLETA (0.0 a 1.0) - Cobre todos os aspectos?

Calcule a MÉDIA dos 4 critérios para obter o score final.

IMPORTANTE: Retorne APENAS um objeto JSON válido no formato:
{{
  "score": <valor entre 0.0 e 1.0>,
  "reasoning": "<explicação detalhada com exemplos específicos, até 150 palavras>"
}}

NÃO adicione nenhum texto antes ou depois do JSON.
"""

    try:
        llm = get_evaluator_llm()
        response = llm.invoke([HumanMessage(content=evaluator_prompt)])
        result = extract_json_from_response(response.content)

        score = float(result.get("score", 0.0))

        return {
            "score": round(score, 4),
            "reasoning": result.get("reasoning", "")
        }

    except Exception as e:
        print(f"❌ Erro ao avaliar Acceptance Criteria Score: {e}")
        return {
            "score": 0.0,
            "reasoning": f"Erro na avaliação: {str(e)}"
        }


def evaluate_user_story_format_score(bug_report: str, user_story: str, reference: str) -> Dict[str, Any]:
    """
    Avalia se a user story segue o formato padrão correto.
    """
    evaluator_prompt = f"""
Você é um avaliador especializado em formato de User Stories ágeis.

BUG REPORT ORIGINAL:
{bug_report}

USER STORY GERADA:
{user_story}

USER STORY ESPERADA (Referência):
{reference}

INSTRUÇÕES:

Avalie o FORMATO da user story gerada:

1. TEMPLATE PADRÃO (0.0 a 1.0) - "Como um..., eu quero..., para que..."?
2. IDENTIFICAÇÃO DE PERSONA (0.0 a 1.0) - "Como um..." é específico?
3. AÇÃO CLARA (0.0 a 1.0) - "Eu quero..." é específico?
4. BENEFÍCIO ARTICULADO (0.0 a 1.0) - "Para que..." tem valor real?
5. SEPARAÇÃO DE SEÇÕES (0.0 a 1.0) - User story separada dos critérios?

Calcule a MÉDIA dos 5 critérios para obter o score final.

IMPORTANTE: Retorne APENAS um objeto JSON válido no formato:
{{
  "score": <valor entre 0.0 e 1.0>,
  "reasoning": "<explicação detalhada com exemplos, até 150 palavras>"
}}

NÃO adicione nenhum texto antes ou depois do JSON.
"""

    try:
        llm = get_evaluator_llm()
        response = llm.invoke([HumanMessage(content=evaluator_prompt)])
        result = extract_json_from_response(response.content)

        score = float(result.get("score", 0.0))

        return {
            "score": round(score, 4),
            "reasoning": result.get("reasoning", "")
        }

    except Exception as e:
        print(f"❌ Erro ao avaliar User Story Format Score: {e}")
        return {
            "score": 0.0,
            "reasoning": f"Erro na avaliação: {str(e)}"
        }


def evaluate_completeness_score(bug_report: str, user_story: str, reference: str) -> Dict[str, Any]:
    """
    Avalia a completude da user story em relação ao bug.
    """
    evaluator_prompt = f"""
Você é um avaliador especializado em completude de User Stories derivadas de bugs.

BUG REPORT ORIGINAL:
{bug_report}

USER STORY GERADA:
{user_story}

USER STORY ESPERADA (Referência):
{reference}

INSTRUÇÕES:

Avalie a COMPLETUDE da user story em relação ao bug:

1. COBERTURA DO PROBLEMA (0.0 a 1.0) - Todos os aspectos do bug cobertos?
2. CONTEXTO TÉCNICO (0.0 a 1.0) - Detalhes técnicos preservados quando relevante?
3. IMPACTO E SEVERIDADE (0.0 a 1.0) - Impacto documentado quando mencionado?
4. TASKS TÉCNICAS (0.0 a 1.0) - Para bugs complexos, há breakdown de tasks?
5. INFORMAÇÕES ADICIONAIS (0.0 a 1.0) - Steps to reproduce, logs, ambiente?

Calcule a MÉDIA dos 5 critérios para obter o score final.

IMPORTANTE:
- Bugs SIMPLES podem ter score alto mesmo sem muitos detalhes técnicos
- Bugs COMPLEXOS DEVEM ter seções adicionais

Retorne APENAS um objeto JSON válido no formato:
{{
  "score": <valor entre 0.0 e 1.0>,
  "reasoning": "<explicação detalhada sobre o que foi bem coberto e o que faltou, até 200 palavras>"
}}

NÃO adicione nenhum texto antes ou depois do JSON.
"""

    try:
        llm = get_evaluator_llm()
        response = llm.invoke([HumanMessage(content=evaluator_prompt)])
        result = extract_json_from_response(response.content)

        score = float(result.get("score", 0.0))

        return {
            "score": round(score, 4),
            "reasoning": result.get("reasoning", "")
        }

    except Exception as e:
        print(f"❌ Erro ao avaliar Completeness Score: {e}")
        return {
            "score": 0.0,
            "reasoning": f"Erro na avaliação: {str(e)}"
        }
