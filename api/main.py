from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from langchain_community.llms import Ollama
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

app = FastAPI()

banned_topics = set()

class TopicRequest(BaseModel):
    topic: str
    
class MessageRequest(BaseModel):
    message: str

# === Routes ===
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

ollama_llm = Ollama(model="llama3.2")
message_check_prompt = PromptTemplate(
    input_variables=["message", "banned"],
    template=(
        "Tu es un modérateur de communauté très strict. "
        "Voici un message utilisateur : \"{message}\".\n"
        "Les sujets interdits sont : {banned}.\n"
        "Ta tâche est de dire si le message parle de l'un de ces sujets, ou de tout les sujets, même de façon indirecte, implicite, avec des synonymes ou un comportement équivalent.\n"
        "Réponds uniquement par OUI ou NON. Ne donne aucune explication. Réponds OUI même si c'est subtil."
    )
)

@app.post("/check-message")
def check_message_for_banned_topics(req: MessageRequest):
    banned = ", ".join(banned_topics)
    if not banned:
        return {"violation": False}

    chain = LLMChain(llm=ollama_llm, prompt=PromptTemplate.from_template(message_check_prompt.template))
    result = chain.run({"message": req.message, "banned": banned})
    return {"violation": result.strip().lower().startswith("oui")}
