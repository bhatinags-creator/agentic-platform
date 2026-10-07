class DeploymentService:
    def create_bundle(self, agent_version_id: str, environment: str) -> dict:
        return {"deployment_id": f"dep-{agent_version_id}-{environment}", "status": "created"}
