"""Prompt templates and OpenAI-backed generation logic.

Demonstrates controlled generation (style/length knobs), prompt templates,
and structured output via OpenAI's JSON-schema response format.
"""
from __future__ import annotations

from openai import OpenAI

from .config import get_settings
from .models import (
    DescriptionLength,
    GenerationConfig,
    ProductDescription,
    ProductInput,
    WritingStyle,
)

# --- Prompt template building blocks -------------------------------------------------

STYLE_GUIDANCE: dict[WritingStyle, str] = {
    WritingStyle.professional: "Polished, credible, and informative. Confident but not hype-driven.",
    WritingStyle.casual: "Friendly, conversational, and relatable. Speak directly to the reader.",
    WritingStyle.luxury: "Elegant, aspirational, and refined. Evoke premium quality and exclusivity.",
    WritingStyle.playful: "Fun, energetic, and witty. Use light humor and vivid language.",
    WritingStyle.technical: "Precise and spec-driven. Emphasize specifications and accuracy.",
    WritingStyle.minimalist: "Clean, concise, and understated. Few words, high impact.",
}

LENGTH_GUIDANCE: dict[DescriptionLength, str] = {
    DescriptionLength.short: "Keep the detailed description to ~2 sentences.",
    DescriptionLength.medium: "Keep the detailed description to ~1 short paragraph (3-4 sentences).",
    DescriptionLength.long: "Write a rich detailed description of 2-3 paragraphs.",
}

SYSTEM_PROMPT = (
    "You are an expert e-commerce copywriter and SEO specialist. "
    "You write compelling, accurate product descriptions that convert browsers into buyers. "
    "Never invent specifications that are not implied by the provided features. "
    "Always respond using the required structured format."
)


def _product_block(product: ProductInput) -> str:
    lines = [f"Product: {product.product_name}"]
    if product.category:
        lines.append(f"Category: {product.category}")
    if product.target_audience:
        lines.append(f"Target audience: {product.target_audience}")
    if product.features:
        feats = "\n".join(f"- {f}" for f in product.features)
        lines.append(f"Features:\n{feats}")
    if product.keywords:
        lines.append("Seed SEO keywords: " + ", ".join(product.keywords))
    return "\n".join(lines)


def _config_block(config: GenerationConfig, variant_hint: str = "") -> str:
    parts = [
        f"Writing style: {config.style.value} — {STYLE_GUIDANCE[config.style]}",
        f"Length: {LENGTH_GUIDANCE[config.length]}",
        "Provide 4-6 key features and 3-5 benefits.",
        "SEO keywords: 5-8 relevant, lowercase phrases.",
        "Meta description must be <= 160 characters.",
    ]
    if variant_hint:
        parts.append(variant_hint)
    return "\n".join(parts)


def build_full_prompt(product: ProductInput, config: GenerationConfig, variant_hint: str = "") -> str:
    return (
        "Write a complete e-commerce product description for the following product.\n\n"
        f"{_product_block(product)}\n\n"
        "Requirements:\n"
        f"{_config_block(config, variant_hint)}"
    )


SECTION_INSTRUCTIONS: dict[str, str] = {
    "title": "Write a single catchy, SEO-friendly product title.",
    "short_description": "Write a punchy short description (1-2 sentences).",
    "detailed_description": "Write the detailed description.",
    "key_features": "Write 4-6 bullet-point key features.",
    "benefits": "Write 3-5 customer-facing benefit bullets.",
    "seo_keywords": "Write 5-8 lowercase SEO keyword phrases.",
    "meta_description": "Write an SEO meta description of <= 160 characters.",
}

LIST_SECTIONS = {"key_features", "benefits", "seo_keywords"}


# --- OpenAI client -------------------------------------------------------------------


def _client() -> OpenAI:
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Copy backend/.env.example to backend/.env and add your key."
        )
    kwargs: dict = {"api_key": settings.openai_api_key}
    if settings.openai_base_url:
        kwargs["base_url"] = settings.openai_base_url
    return OpenAI(**kwargs)


def generate_description(
    product: ProductInput, config: GenerationConfig, variant_hint: str = ""
) -> ProductDescription:
    """Generate one full structured product description."""
    client = _client()
    settings = get_settings()
    completion = client.beta.chat.completions.parse(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_full_prompt(product, config, variant_hint)},
        ],
        response_format=ProductDescription,
        temperature=0.8,
    )
    parsed = completion.choices[0].message.parsed
    if parsed is None:
        raise RuntimeError("Model returned no structured content.")
    return parsed


def generate_variants(product: ProductInput, config: GenerationConfig) -> list[ProductDescription]:
    """Generate N distinct variants, nudging each to differ."""
    variants: list[ProductDescription] = []
    for i in range(config.num_variants):
        hint = ""
        if config.num_variants > 1:
            hint = (
                f"This is variant #{i + 1} of {config.num_variants}. "
                "Make it meaningfully different from other variants in angle and wording."
            )
        variants.append(generate_description(product, config, hint))
    return variants


def regenerate_section(product: ProductInput, config: GenerationConfig, section: str):
    """Regenerate a single section and return its value (str or list[str])."""
    if section not in SECTION_INSTRUCTIONS:
        raise ValueError(f"Unknown section: {section}")

    client = _client()
    settings = get_settings()
    is_list = section in LIST_SECTIONS

    if is_list:
        schema = {
            "type": "object",
            "properties": {"items": {"type": "array", "items": {"type": "string"}}},
            "required": ["items"],
            "additionalProperties": False,
        }
    else:
        schema = {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
            "additionalProperties": False,
        }

    user_prompt = (
        f"{SECTION_INSTRUCTIONS[section]}\n\n"
        f"{_product_block(product)}\n\n"
        f"{_config_block(config)}\n\n"
        "Return only this one section."
    )

    completion = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {"name": "section", "schema": schema, "strict": True},
        },
        temperature=0.9,
    )
    import json

    data = json.loads(completion.choices[0].message.content or "{}")
    return data["items"] if is_list else data["text"]
