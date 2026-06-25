import os
from concurrent import futures

import grpc
from grpc_reflection.v1alpha import reflection

import protopilot_pb2
import protopilot_pb2_grpc


WORKFLOWS = [
    {"id": 1, "name": "Quarterly Access Review", "owner": "IAM Team", "status": "healthy"},
    {"id": 2, "name": "Expense Approval Automation", "owner": "Finance Ops", "status": "healthy"},
    {"id": 3, "name": "Cloud Resource Cleanup", "owner": "Platform", "status": "paused"},
    {"id": 4, "name": "Incident Escalation Router", "owner": "SecOps", "status": "degraded"},
    {"id": 5, "name": "Vendor Intake Workflow", "owner": "Procurement", "status": "healthy"},
]


class WorkflowService(protopilot_pb2_grpc.WorkflowServiceServicer):
    def ListWorkflows(self, request, context):
        items = [
            protopilot_pb2.Workflow(
                id=wf["id"], name=wf["name"], owner=wf["owner"], status=wf["status"]
            )
            for wf in WORKFLOWS
        ]
        return protopilot_pb2.ListWorkflowsResponse(workflows=items)


class AdminService(protopilot_pb2_grpc.AdminServiceServicer):
    def TestRule(self, request, context):
        metadata = dict(context.invocation_metadata())
        role = metadata.get("x-user-role")

        # Intentionally vulnerable: trusts caller-controlled metadata role.
        if role != "admin":
            context.abort(grpc.StatusCode.PERMISSION_DENIED, "admin role required")

        expression = request.expression or ""
        lowered = expression.lower()

        # Weak denylist-based sandbox, intentionally bypassable for CTF.
        blocked = ["import", "os", "subprocess", "system", "popen", "open", "read"]
        for token in blocked:
            if token in lowered:
                return protopilot_pb2.TestRuleResponse(result="blocked expression")

        helper = lambda value: value
        eval_context = {
            "amount": 750,
            "department": "finance",
            "risk_score": 8,
            "approved": False,
            "helper": helper,
        }

        try:
            result = eval(expression, {"__builtins__": {}}, eval_context)
            return protopilot_pb2.TestRuleResponse(result=str(result))
        except Exception as exc:
            return protopilot_pb2.TestRuleResponse(result=f"error: {exc}")


def serve() -> None:
    port = int(os.environ.get("PORT", "50051"))
    enable_reflection = os.environ.get("ENABLE_REFLECTION", "true").lower() == "true"

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=8))
    protopilot_pb2_grpc.add_WorkflowServiceServicer_to_server(WorkflowService(), server)
    protopilot_pb2_grpc.add_AdminServiceServicer_to_server(AdminService(), server)

    if enable_reflection:
        service_names = (
            protopilot_pb2.DESCRIPTOR.services_by_name["WorkflowService"].full_name,
            protopilot_pb2.DESCRIPTOR.services_by_name["AdminService"].full_name,
            reflection.SERVICE_NAME,
        )
        reflection.enable_server_reflection(service_names, server)

    server.add_insecure_port(f"[::]:{port}")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
