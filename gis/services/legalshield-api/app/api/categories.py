"""GET /api/v1/legalshield/categories
       /api/v1/legalshield/categories/{code}
       /api/v1/legalshield/categories/{code}/routing

Expose curated problem-category catalog + tier-based routing knowledge.
Read-only, no auth, safe to cache aggressively.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session

router = APIRouter()


# ─── catalog ─────────────────────────────────────────────────────────


@router.get("/categories", summary="List problem categories (12 canonical)")
async def list_categories(
    severity: Optional[str] = Query(
        None,
        regex="^(critical|high|medium|low)$",
        description="Filter by severity_default",
    ),
    tag: Optional[str] = Query(None, description="Filter by single tag (e.g. 'gender')"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    sql = text(
        """
        SELECT code, name_ja, name_en, description_ja,
               severity_default, urgent_hotline,
               parent_code, tags, display_order
        FROM legalshield.problem_category
        WHERE is_active = TRUE
          AND (CAST(:sev AS text) IS NULL OR severity_default = :sev)
          AND (CAST(:tag AS text) IS NULL OR :tag = ANY(tags))
        ORDER BY display_order, code
        """
    )
    rows = (
        await session.execute(sql, {"sev": severity, "tag": tag})
    ).mappings().all()
    return {"count": len(rows), "categories": [dict(r) for r in rows]}


@router.get("/categories/{code}", summary="Single problem category detail")
async def get_category(
    code: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    sql = text(
        """
        SELECT code, name_ja, name_en, description_ja,
               severity_default, urgent_hotline,
               parent_code, tags, display_order, is_active, created_at
        FROM legalshield.problem_category
        WHERE code = :code
        """
    )
    row = (await session.execute(sql, {"code": code})).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail=f"category '{code}' not found")
    return dict(row)


# ─── routing tiers ───────────────────────────────────────────────────


@router.get(
    "/categories/{code}/routing",
    summary="Tier-based routing knowledge for a category",
)
async def get_routing(
    code: str,
    tier: Optional[int] = Query(None, ge=1, le=5, description="Filter by tier"),
    trigger: Optional[str] = Query(
        None,
        description="Filter to routes whose trigger_condition is 'always' OR matches this value",
    ),
    session: AsyncSession = Depends(get_session),
) -> dict:
    # confirm category exists (clearer 404 vs empty list)
    exists = (
        await session.execute(
            text("SELECT 1 FROM legalshield.problem_category WHERE code = :c"),
            {"c": code},
        )
    ).scalar()
    if not exists:
        raise HTTPException(status_code=404, detail=f"category '{code}' not found")

    sql = text(
        """
        SELECT id, category_code, tier, org_kind, org_name_pattern,
               weight, trigger_condition,
               what_to_say_ja, documents_needed_ja,
               expected_outcome_ja, next_tier_if_ja, notes_ja, source
        FROM legalshield.category_routing
        WHERE category_code = :code
          AND (CAST(:tier AS int) IS NULL OR tier = :tier)
          AND (
            CAST(:trigger AS text) IS NULL
            OR trigger_condition = 'always'
            OR trigger_condition = :trigger
          )
        ORDER BY tier, weight DESC
        """
    )
    rows = (
        await session.execute(sql, {"code": code, "tier": tier, "trigger": trigger})
    ).mappings().all()

    # group by tier for easier client rendering
    tiers: dict[int, list[dict]] = {}
    for r in rows:
        tiers.setdefault(int(r["tier"]), []).append(dict(r))

    return {
        "category_code": code,
        "tier_count": len(tiers),
        "total_routes": len(rows),
        "tiers": [
            {"tier": t, "routes": tiers[t]}
            for t in sorted(tiers.keys())
        ],
    }
