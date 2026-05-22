from pydantic import BaseModel

class ExcludeNoneModel(BaseModel):
    def model_post_init(self, __context):
        for field, value in list(self.__dict__.items()):
            if value is None:
                delattr(self, field)