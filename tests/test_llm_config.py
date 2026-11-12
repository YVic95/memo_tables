def test_shared_llm_uses_claude_haiku_through_openrouter(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")
    from graphs.llm import llm

    assert llm.model_name == "anthropic/claude-haiku-5.5"
    assert llm.openai_api_base == "https://openrouter.ai/api/v1"
