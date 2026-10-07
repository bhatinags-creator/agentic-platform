import pytest

from services.prompt_management.service import PromptManagementService, PromptValidationError


def test_prompt_template_version_and_render_flow() -> None:
    service = PromptManagementService()
    template = service.create_template(
        tenant_id="tenant-a",
        name="Support Reply",
        owner="support-team",
    )
    version = service.create_version(
        tenant_id="tenant-a",
        template_id=template.template_id,
        version="1.0.0",
        template_text="Hello {customer_name}, answer about {topic}.",
    )
    published = service.publish_version("tenant-a", version.version_id)
    rendered = service.render(
        tenant_id="tenant-a",
        version_id=published.version_id,
        variables={"customer_name": "Asha", "topic": "refunds"},
    )

    assert published.status == "published"
    assert published.variables == ["customer_name", "topic"]
    assert rendered.rendered_text == "Hello Asha, answer about refunds."


def test_prompt_render_requires_all_variables() -> None:
    service = PromptManagementService()
    template = service.create_template(tenant_id="tenant-a", name="Prompt", owner="team")
    version = service.create_version(
        tenant_id="tenant-a",
        template_id=template.template_id,
        version="1.0.0",
        template_text="Hello {name}",
    )

    with pytest.raises(PromptValidationError):
        service.render(tenant_id="tenant-a", version_id=version.version_id, variables={})
