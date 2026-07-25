"""Gemini-backed model wrapper used by the planner, researcher, critic, and writer nodes."""
from __future__ import annotations

import logging

from app.models.schemas import Claim, ResearchAngle, ResearchMethod, SourceDoc, SubQuestion, VerifiedClaim
from app.services.gemini_api import GeminiAPIClient

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self, model: str | None = None):
        self.model = model
        self._client = GeminiAPIClient(model=model)

    @property
    def is_configured(self) -> bool:
        return self._client.is_configured

    async def generate_sub_questions(
        self, *, query: str, system_prompt: str, user_prompt: str
    ) -> list[SubQuestion]:
        if not self.is_configured:
            raise RuntimeError(
                "GEMINI_API_KEY is not configured; cannot call generate_sub_questions()."
            )

        payload = await self._client.generate_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_output_tokens=2000,
        )
        raw_items = payload.get("sub_questions", [])
        if not raw_items:
            raise RuntimeError("Gemini returned an empty sub-question list.")

        sub_questions: list[SubQuestion] = []
        for item in raw_items:
            sub_questions.append(
                SubQuestion(
                    parent_query=query,
                    question_text=item["question_text"],
                    rationale=item.get("rationale", ""),
                    angle=ResearchAngle(item["angle"]),
                    research_method=ResearchMethod(item["research_method"]),
                    priority=int(item.get("priority", 2)),
                )
            )
        return sub_questions

    async def extract_claims(
        self,
        *,
        sub_question: SubQuestion,
        source_docs: list[SourceDoc],
        system_prompt: str,
        user_prompt: str,
    ) -> list[Claim]:
        if not self.is_configured:
            raise RuntimeError("GEMINI_API_KEY is not configured; cannot call extract_claims().")

        payload = await self._client.generate_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_output_tokens=1500,
        )

        url_to_doc_id = {doc.url: doc.id for doc in source_docs}
        claims: list[Claim] = []
        for item in payload.get("claims", []):
            source_doc_id = url_to_doc_id.get(item.get("source_url"))
            if source_doc_id is None:
                logger.warning(
                    "extract_claims: dropping claim with unrecognized source_url=%r",
                    item.get("source_url"),
                )
                continue
            claims.append(
                Claim(
                    source_doc_id=source_doc_id,
                    sub_question_id=sub_question.id,
                    claim_text=item["claim_text"],
                    confidence=float(item.get("confidence", 0.5)),
                    supporting_excerpt=item.get("supporting_excerpt", ""),
                )
            )
        return claims

    async def extract_and_verify_claims(
        self, *, source_docs: list[SourceDoc], system_prompt: str, user_prompt: str
    ) -> list[dict]:
        if not self.is_configured:
            raise RuntimeError(
                "GEMINI_API_KEY is not configured; cannot call extract_and_verify_claims()."
            )

        payload = await self._client.generate_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_output_tokens=4000,
        )

        known_urls = {doc.url for doc in source_docs}
        evidence: list[dict] = []
        for item in payload.get("claims", []):
            primary_url = item.get("primary_source_url")
            if primary_url not in known_urls:
                logger.warning(
                    "extract_and_verify_claims: dropping claim with unrecognized primary_source_url=%r",
                    primary_url,
                )
                continue

            supporting = [u for u in item.get("supporting_source_urls", []) if u in known_urls]
            contradicting = [u for u in item.get("contradicting_source_urls", []) if u in known_urls]

            evidence.append(
                {
                    "claim_text": item["claim_text"],
                    "primary_source_url": primary_url,
                    "supporting_source_urls": supporting,
                    "contradicting_source_urls": contradicting,
                    "critic_notes": item.get("critic_notes", ""),
                }
            )
        return evidence

    async def refine_search_query(
        self,
        *,
        sub_question: SubQuestion,
        problematic_claims: list[VerifiedClaim],
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        if not self.is_configured:
            raise RuntimeError("GEMINI_API_KEY is not configured; cannot call refine_search_query().")

        payload = await self._client.generate_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_output_tokens=300,
        )

        refined_query = (payload.get("refined_query") or "").strip()
        if not refined_query:
            raise RuntimeError("Gemini returned an empty refined query.")
        return refined_query

    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        if not self.is_configured:
            raise RuntimeError("GEMINI_API_KEY is not configured; cannot call complete().")

        text = await self._client.generate_text(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_output_tokens=400,
        )
        if not text:
            raise RuntimeError("Model response contained no text content.")
        return text

    async def complete_structured(self, system_prompt: str, user_prompt: str, schema: type) -> object:
        raise NotImplementedError("Wire this up for the writer node.")


def build_llm_client() -> LLMClient:
    return LLMClient()