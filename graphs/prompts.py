from langchain_core.prompts import PromptTemplate

propose_rules_prompt = PromptTemplate.from_template(
    """
        You are a language-learning content expert.

        Suggest exactly 5 fundamental grammar or usage rules a native
        {native_language} speaker should learn first when studying
        {target_language}.

        Keep explanations concise and beginner-friendly.

        Rules should be written in the {native_language} of the user.
    """
)