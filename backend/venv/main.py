# from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
# from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel
# from typing import List, Optional
# import jwt
# import pandas as pd
# from datetime import datetime, timedelta
# from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
# import json
# import jwt

# app = FastAPI(title="Sentiment Analysis API")
# async def read_root():
#     return{"Hello":"world"}
# # CORS middleware configuration
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # In production, replace with specific origins
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Security configurations
# SECRET_KEY = "your-secret-key"  # In production, use environment variable
# ALGORITHM = "HS256"
# ACCESS_TOKEN_EXPIRE_MINUTES = 30

# # Initialize sentiment analyzer
# sentiment_analyzer = SentimentIntensityAnalyzer()

# # Pydantic models
# class Token(BaseModel):
#     access_token: str
#     token_type: str

# class User(BaseModel):
#     username: str
#     password: str

# class TextInput(BaseModel):
#     text: str

# class SentimentResult(BaseModel):
#     text: str
#     sentiment: float
#     timestamp: Optional[datetime]

# # User database (replace with actual database in production)
# users_db = {
#     "admin": {
#         "username": "admin",
#         "hashed_password": "hashed_admin_password"  # Use proper hashing in production
#     }
# }

# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# # Authentication functions
# def create_access_token(data: dict):
#     to_encode = data.copy()
#     expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
#     to_encode.update({"exp": expire})
#     encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
#     return encoded_jwt

# async def get_current_user(token: str = Depends(oauth2_scheme)):
#     try:
#         payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
#         username: str = payload.get("sub")
#         if username is None:
#             raise HTTPException(status_code=401, detail="Invalid authentication credentials")
#     except jwt.JWTError:
#         raise HTTPException(status_code=401, detail="Invalid authentication credentials")
#     return username

# # Endpoints
# @app.post("/token", response_model=Token)
# async def login(form_data: OAuth2PasswordRequestForm = Depends()):
#     user = users_db.get(form_data.username)
#     if not user or form_data.password != "admin_password":  # Use proper password verification in production
#         raise HTTPException(status_code=400, detail="Incorrect username or password")
    
#     access_token = create_access_token(data={"sub": user["username"]})
#     return {"access_token": access_token, "token_type": "bearer"}

# @app.post("/analyze/text", response_model=SentimentResult)
# async def analyze_text(text_input: TextInput, current_user: str = Depends(get_current_user)):
#     scores = sentiment_analyzer.polarity_scores(text_input.text)
#     return SentimentResult(
#         text=text_input.text,
#         sentiment=scores["compound"],
#         timestamp=datetime.now()
#     )

# @app.post("/analyze/file")
# async def analyze_file(file: UploadFile = File(...), current_user: str = Depends(get_current_user)):
#     if not file.filename.endswith('.csv'):
#         raise HTTPException(status_code=400, detail="Only CSV files are supported")
    
#     try:
#         df = pd.read_csv(file.file)
#         required_columns = ['id', 'text']
#         if not all(col in df.columns for col in required_columns):
#             raise HTTPException(status_code=400, detail="CSV must contain 'id' and 'text' columns")
        
#         results = []
#         for _, row in df.iterrows():
#             scores = sentiment_analyzer.polarity_scores(row['text'])
#             timestamp = row.get('timestamp', datetime.now().isoformat())
#             results.append({
#                 'id': row['id'],
#                 'text': row['text'],
#                 'sentiment': scores['compound'],
#                 'timestamp': timestamp
#             })
        
#         return {
#             'results': results,
#             'summary': {
#                 'positive': len([r for r in results if r['sentiment'] > 0.05]),
#                 'neutral': len([r for r in results if -0.05 <= r['sentiment'] <= 0.05]),
#                 'negative': len([r for r in results if r['sentiment'] < -0.05])
#             }
#         }
    
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)


from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import os
from typing import List

# Initialize FastAPI app
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Authentication setup
security = HTTPBasic()
VALID_USERNAME = "user"
VALID_PASSWORD = "pass"

# Pre-trained sentiment analysis model
analyzer = SentimentIntensityAnalyzer()

# Authentication dependency
def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    if credentials.username == VALID_USERNAME and credentials.password == VALID_PASSWORD:
        return credentials.username
    raise HTTPException(status_code=401, detail="Unauthorized")

# Response model for sentiment analysis
class SentimentResponse(BaseModel):
    id: int
    text: str
    sentiment: str
    score: float

@app.post("/analyze", response_model=List[SentimentResponse])
def analyze_file(file: UploadFile = File(...), user: str = Depends(authenticate)):
    try:
        # Read the uploaded file
        contents = file.file.read()
        data = pd.read_csv(pd.compat.StringIO(contents.decode("utf-8")))
        
        if "id" not in data.columns or "text" not in data.columns:
            raise HTTPException(status_code=400, detail="CSV must contain 'id' and 'text' columns.")
        
        results = []
        for _, row in data.iterrows():
            sentiment_scores = analyzer.polarity_scores(row["text"])
            sentiment = "positive" if sentiment_scores['compound'] >= 0.05 else "negative" if sentiment_scores['compound'] <= -0.05 else "neutral"
            results.append(SentimentResponse(
                id=row["id"],
                text=row["text"],
                sentiment=sentiment,
                score=sentiment_scores['compound']
            ))
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {e}")
