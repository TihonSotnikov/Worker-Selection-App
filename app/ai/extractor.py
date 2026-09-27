import logging

from lmformatenforcer import JsonSchemaParser
from lmformatenforcer.integrations.transformers import build_transformers_prefix_allowed_tokens_fn
from transformers import pipeline

from app.core.schemas import CandidateSummary

SYSTEM_PROMPT_EXTRACT = """..."""  # (промпт остается прежним)


class Extractor:
    def __init__(self, model_name: str, logger: logging.Logger = None, **kwargs):
        if logger:
            logger.info(f"Initializing extractor with model {model_name}...")
        self._pipeline = pipeline(
            "text-generation",
            model=model_name,
            device_map="auto",
            dtype="auto",
            **kwargs,
        )
        self._sum_parser = JsonSchemaParser(CandidateSummary.model_json_schema())
        self._sum_prefix_func = build_transformers_prefix_allowed_tokens_fn(self._pipeline.tokenizer, self._sum_parser)
        self._logger = logger

    def __call__(self, prompt, **kwds):
        sum_json_str = self._pipeline(
            [
                [
                    {"role": "system", "content": SYSTEM_PROMPT_EXTRACT},
                    {"role": "user", "content": prompt + " /no_think"},
                ]
            ],
            max_new_tokens=2048,
            prefix_allowed_tokens_fn=self._sum_prefix_func,
            repetition_penalty=1.15,
            return_full_text=False,
            **kwds,
        )[-1]

        sum_json_str = sum_json_str[0]["generated_text"].strip("\n ")
        try:
            candidate_summary = CandidateSummary.model_validate_json(sum_json_str)
            return candidate_summary.full_name, candidate_summary.raw_summary, candidate_summary.vector
        except Exception as e:
            if self._logger:
                self._logger.error(f"JSON Parsing error: {e}")
            raise e
