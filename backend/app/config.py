from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    AMADEUS_CLIENT_ID: str
    AMADEUS_CLIENT_SECRET: str
    AMADEUS_HOSTNAME: str = "test"
    
    SERPAPI_KEY: str
    
    # AI Config
    AI_PROVIDER: str = "gemini" # or "openai"
    GOOGLE_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    
    ENV: str = "development"
    DEBUG: bool = True
    
    # Currency Rates (Fallback for Test API)
    EXCHANGE_RATE_EUR_JPY: float = 162.0
    EXCHANGE_RATE_USD_JPY: float = 150.0
    
    # Web Scraper Settings
    SCRAPER_HEADLESS: bool = False  # false = ブラウザ表示, true = 非表示
    SCRAPER_AUTO_CLOSE: bool = True  # true = 自動閉じる, false = 開いたまま

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
