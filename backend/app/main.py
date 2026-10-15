from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict, Field

app = FastAPI(title="Custra API")


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Custra Backend"
    }


class TestIssue(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    product_name: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=2000)


@app.post("/api/test-issue")
def submit_test_issue(issue: TestIssue):
    return {
        "success": True,
        "message": "Test issue submitted successfully!",
        **issue.model_dump(),
        "status": "received",
    }
