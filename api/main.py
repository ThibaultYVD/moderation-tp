from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from langchain_community.llms import Ollama
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
import os

app = FastAPI()

banned_topics = set()

class TopicRequest(BaseModel):
    topic: str

class MessageRequest(BaseModel):
    message: str

@app.post("/ban-topic")
def add_banned_topic(req: TopicRequest):
    topic = req.topic.strip().lower()
    if topic in banned_topics:
        raise HTTPException(status_code=400, detail="Sujet déjà banni.")
    banned_topics.add(topic)
    return {"message": f"Sujet '{topic}' ajouté à la liste des sujets bannis."}

@app.delete("/ban-topic")
def remove_banned_topic(req: TopicRequest):
    topic = req.topic.strip().lower()
    if topic not in banned_topics:
        raise HTTPException(status_code=404, detail="Sujet non trouvé dans la liste des bannis.")
    banned_topics.remove(topic)
    return {"message": f"Sujet '{topic}' supprimé de la liste des sujets bannis."}

@app.get("/ban-topic")
def list_banned_topics():
    return {"banned_topics": list(banned_topics)}

# === LLM avec prompt système ===
ollama_llm = Ollama(
    model="llama3.2",
    base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
    system="Tu es un modérateur très strict d’un serveur Discord francophone. "
           "Ta mission est de détecter si un message contient un sujet interdit, "
           "même si c’est indirect, implicite, ou formulé de manière détournée. "
           "Tu dois répondre uniquement par 'OUI' ou 'NON'."
)

message_check_prompt = PromptTemplate(
    input_variables=["message", "banned"],
    template=(
        "Voici un message utilisateur : \"{message}\"\n"
        "Les sujets interdits sont : {banned}.\n"
        "Ce message enfreint-il l’un des sujets interdits ? Réponds par OUI ou NON uniquement."
    )
)

@app.post("/check-message")
def check_message_for_banned_topics(req: MessageRequest):
    banned = ", ".join(banned_topics)
    if not banned:
        return {"violation": False, "reason": "aucun sujet banni"}

    prompt_text = message_check_prompt.format(message=req.message, banned=banned)
    chain = LLMChain(llm=ollama_llm, prompt=PromptTemplate.from_template(message_check_prompt.template))
    result = chain.run({"message": req.message, "banned": banned})

    return {
        "violation": result.strip().lower().startswith("oui"),
        "raw": result.strip(),
        "prompt": prompt_text
    }
