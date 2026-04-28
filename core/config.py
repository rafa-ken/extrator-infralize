from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    groq_api_key: str
    groq_model: str = "llama-3.3-70b-versatile"

    # Qualidade mínima de confiança do OCR para não emitir aviso
    ocr_confidence_threshold: float = 40.0

    # Idioma do Tesseract (por padrão português + inglês)
    tesseract_lang: str = "por+eng"

    # Caminho para o bin do Poppler (necessário no Windows se não estiver no PATH)
    poppler_path: str | None = None

    # Caminho para o executável do Tesseract (necessário no Windows se não estiver no PATH)
    tesseract_cmd: str | None = None


settings = Settings()
