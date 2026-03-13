from src.models.base import Model, ModelResult

class LocalModel(Model):

    def __init__(self, model_name: str):
        self.name = model_name

    def generate(self, prompt: str) -> ModelResult:
        raise NotImplementedError("LocalModel.generate not implemented yet")