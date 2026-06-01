"""
CLI tool to approve or reject pending remediation plans.

Usage:
    python scripts/approve.py --list
    python scripts/approve.py --approve <plan_id>
    python scripts/approve.py --reject <plan_id> --note "too risky"
"""
import argparse
import asyncio
import sys
import httpx


GATEWAY_URL = "http://localhost:8000"


async def list_pending() -> None:
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{GATEWAY_URL}/approvals/pending")
            r.raise_for_status()
            approvals = r.json()
            if not approvals:
                print("No pending approvals.")
                return
            print(f"\n{'PLAN ID':<12} {'INCIDENT':<14} {'LABEL':<25} {'RISK':<6} {'REASON':<20} EXPIRES")
            print("-" * 100)
            for a in approvals:
                print(
                    f"{a['plan_id']:<12} "
                    f"{a['incident_id']:<14} "
                    f"{a['plan_label']:<25} "
                    f"{a['risk_score']:<6.2f} "
                    f"{a['reason']:<20} "
                    f"{a['expires_at']}"
                )
    except Exception as e:
        print(f"Error fetching approvals: {e}")
        print("Is the gateway running? uvicorn gateway.main:app --reload")


async def approve(plan_id: str) -> None:
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(f"{GATEWAY_URL}/approvals/{plan_id}/approve")
            r.raise_for_status()
            print(f"Plan {plan_id} approved.")
    except Exception as e:
        print(f"Error approving plan: {e}")


async def reject(plan_id: str, note: str) -> None:
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{GATEWAY_URL}/approvals/{plan_id}/reject",
                json={"note": note},
            )
            r.raise_for_status()
            print(f"Plan {plan_id} rejected. Note: {note}")
    except Exception as e:
        print(f"Error rejecting plan: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Corvus approval CLI")
    parser.add_argument("--list",    action="store_true",  help="List pending approvals")
    parser.add_argument("--approve", metavar="PLAN_ID",    help="Approve a plan")
    parser.add_argument("--reject",  metavar="PLAN_ID",    help="Reject a plan")
    parser.add_argument("--note",    default="",           help="Rejection note")
    args = parser.parse_args()

    if args.list:
        asyncio.run(list_pending())
    elif args.approve:
        asyncio.run(approve(args.approve))
    elif args.reject:
        asyncio.run(reject(args.reject, args.note))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
