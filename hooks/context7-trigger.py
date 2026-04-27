#!/usr/bin/env python3
"""Context7 proactive trigger (versionado no Harness v3 SDD).

Le o prompt do usuario via stdin (JSON UserPromptSubmit), detecta mencoes a
bibliotecas/frameworks/SDKs/APIs e injeta lembrete para usar Context7 antes de
responder. Prioriza precisao: sem falsos positivos em palavras genericas.

Espelhado em ~/.claude/hooks/context7-trigger.py — versionar aqui torna a
config reproduzivel via git clone do plugin.
"""
from __future__ import annotations

import json
import re
import sys

LIBS = {
    # JS/TS frameworks
    "react", "next.js", "nextjs", "vue", "vuejs", "angular", "svelte",
    "sveltekit", "nuxt", "remix", "astro", "solid.js", "solidjs", "qwik",
    # JS/TS libs
    "tanstack", "react query", "react-query", "redux", "zustand", "jotai",
    "tailwind", "tailwindcss", "shadcn", "shadcn/ui", "radix", "mui",
    "chakra", "bootstrap", "framer motion", "framer-motion",
    "express", "fastify", "koa", "hono", "nestjs", "trpc", "drizzle",
    "prisma", "mongoose", "sequelize", "kysely",
    "vite", "webpack", "rollup", "turbopack", "esbuild",
    "vitest", "jest", "playwright", "cypress", "testing-library",
    # Python frameworks/libs
    "fastapi", "django", "flask", "starlette", "litestar", "pyramid",
    "pydantic", "sqlalchemy", "alembic", "celery", "rq",
    "pandas", "numpy", "polars", "scipy", "matplotlib", "seaborn",
    "pytorch", "tensorflow", "keras", "scikit-learn", "sklearn",
    "transformers", "huggingface", "hugging face",
    "langchain", "llamaindex", "llama-index", "langgraph", "haystack",
    "pytest", "ruff", "pyright", "mypy", "black",
    # AI/LLM SDKs
    "anthropic sdk", "claude api", "claude agent sdk", "openai sdk",
    "openai api", "google ai", "gemini api", "bedrock", "vertex ai",
    "ollama", "vllm", "llama.cpp",
    # Cloud/infra
    "supabase", "firebase", "vercel", "netlify", "cloudflare workers",
    "aws lambda", "aws sdk", "boto3", "azure sdk", "gcp", "cloud run",
    "kubernetes", "k8s", "helm", "terraform", "pulumi", "ansible",
    "docker compose", "docker-compose", "podman",
    # Backend infra
    "redis", "postgres", "postgresql", "mongodb", "cassandra", "kafka",
    "rabbitmq", "elasticsearch", "opensearch", "duckdb", "clickhouse",
    # Mobile/desktop
    "react native", "react-native", "expo", "flutter", "swiftui",
    "tauri", "electron",
    # MCP/agent
    "mcp server", "mcp protocol", "model context protocol",
    "claude code", "claude agent", "agent sdk",
    # Other
    "fastmcp", "zod", "yup", "valibot", "graphql", "apollo",
    "hasura", "strapi", "directus", "sanity", "contentful",
    "stripe sdk", "stripe api", "twilio", "sendgrid", "resend",
    "playwright python", "selenium", "beautifulsoup", "scrapy",
}

VERB_PATTERNS = re.compile(
    r"\b("
    r"como (usar|instalar|configurar|implementar|integrar|migrar)|"
    r"qual (a )?api|qual (o )?metodo|"
    r"docs? d[eo]|documenta[cç][aã]o d[eo]|"
    r"versao d[eo]|version[aã]o d[eo]|"
    r"latest version|breaking change|changelog|migration guide|"
    r"setup d[eo]|getting started"
    r")\b",
    re.IGNORECASE,
)

SKIP_IF_PRESENT = re.compile(
    r"\b(context7|resolve-library-id|query-docs|/ctx-|microsoft_docs_)\b",
    re.IGNORECASE,
)


def detect(prompt: str) -> list[str]:
    if SKIP_IF_PRESENT.search(prompt):
        return []
    low = prompt.lower()
    hits = sorted({lib for lib in LIBS if lib in low})
    if not hits and VERB_PATTERNS.search(prompt):
        return ["__verb_only__"]
    return hits


def build_message(hits: list[str]) -> str:
    if hits == ["__verb_only__"]:
        return (
            "[context7-hint] Pergunta menciona docs/setup/versao. Antes de responder, "
            "considere `mcp__plugin_context7_context7__resolve-library-id` + `query-docs` "
            "para puxar documentacao oficial atual."
        )
    sample = ", ".join(hits[:5])
    return (
        f"[context7-hint] Detectadas libs/frameworks: {sample}. "
        "OBRIGATORIO antes de gerar codigo ou orientacao API-especifica: "
        "1) `mcp__plugin_context7_context7__resolve-library-id` para o(s) pacote(s); "
        "2) `query-docs` com a pergunta especifica. "
        "Ignore apenas se o usuario explicitamente pediu para nao consultar docs."
    )


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    prompt = payload.get("prompt", "") or ""
    if not prompt or len(prompt) < 8:
        return 0
    hits = detect(prompt)
    if not hits:
        return 0
    out = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": build_message(hits),
        }
    }
    sys.stdout.write(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
