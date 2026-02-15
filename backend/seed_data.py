"""
Seed Script - Populate database with demo data for presentation
Run with: python seed_data.py
"""

import sys
sys.path.insert(0, '.')

from datetime import datetime, timedelta
import random

from app.database import engine, SessionLocal, Base
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message


def seed_database():
    """Seed database with demo data"""
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        # Check if already seeded
        if db.query(User).count() > 0:
            print("Database already seeded. Skipping...")
            return
        
        print("[*] Seeding database with demo data...")
        
        # Create demo users
        users = [
            User(
                name="Maria Rodriguez",
                email="maria.rodriguez@email.com",
                avatar_initials="MR",
                preferred_language="es",
                language_name="Spanish",
                language_flag="🇪🇸",
                is_premium=True
            ),
            User(
                name="Ahmed Khan",
                email="ahmed.khan@email.com",
                avatar_initials="AK",
                preferred_language="ar",
                language_name="Arabic",
                language_flag="🇸🇦",
                is_premium=False
            ),
            User(
                name="Lin Chen",
                email="lin.chen@email.com",
                avatar_initials="LC",
                preferred_language="zh-cn",
                language_name="Chinese",
                language_flag="🇨🇳",
                is_premium=False
            ),
            User(
                name="John Smith",
                email="john.smith@email.com",
                avatar_initials="JS",
                preferred_language="en",
                language_name="English",
                language_flag="🇺🇸",
                is_premium=True
            ),
            User(
                name="Sophie Petit",
                email="sophie.petit@email.com",
                avatar_initials="SP",
                preferred_language="fr",
                language_name="French",
                language_flag="🇫🇷",
                is_premium=False
            ),
        ]
        
        for user in users:
            db.add(user)
        db.commit()
        print(f"[OK] Created {len(users)} demo users")
        
        # Create conversations
        conversations_data = [
            {
                "customer": users[0],
                "status": "active",
                "sentiment": "negative",
                "frustration": 0.87,
                "escalated": False,
                "language": ("es", "Spanish", "🇪🇸"),
                "preview": "I still haven't received my order..."
            },
            {
                "customer": users[1],
                "status": "active",
                "sentiment": "positive",
                "frustration": 0.1,
                "escalated": False,
                "language": ("ar", "Arabic", "🇸🇦"),
                "preview": "Thank you for your help!"
            },
            {
                "customer": users[2],
                "status": "pending",
                "sentiment": "neutral",
                "frustration": 0.3,
                "escalated": False,
                "language": ("zh-cn", "Chinese", "🇨🇳"),
                "preview": "How do I return this item?"
            },
            {
                "customer": users[3],
                "status": "escalated",
                "sentiment": "negative",
                "frustration": 0.95,
                "escalated": True,
                "language": ("en", "English", "🇺🇸"),
                "preview": "This is unacceptable! Manager!"
            },
            {
                "customer": users[4],
                "status": "resolved",
                "sentiment": "positive",
                "frustration": 0.05,
                "escalated": False,
                "language": ("fr", "French", "🇫🇷"),
                "preview": "Merci beaucoup pour votre aide!"
            },
        ]
        
        for i, conv_data in enumerate(conversations_data):
            conv = Conversation(
                customer_id=conv_data["customer"].id,
                status=conv_data["status"],
                priority="urgent" if conv_data["escalated"] else "normal",
                current_sentiment=conv_data["sentiment"],
                sentiment_score=0.3 if conv_data["sentiment"] == "negative" else 0.7,
                frustration_level=conv_data["frustration"],
                is_escalated=conv_data["escalated"],
                escalation_reason="High frustration level" if conv_data["escalated"] else None,
                detected_language=conv_data["language"][0],
                language_name=conv_data["language"][1],
                language_flag=conv_data["language"][2],
                last_message_preview=conv_data["preview"],
                message_count=random.randint(3, 8),
                created_at=datetime.utcnow() - timedelta(minutes=random.randint(5, 120))
            )
            db.add(conv)
        db.commit()
        print(f"[OK] Created {len(conversations_data)} demo conversations")
        
        # Create messages for first conversation (Maria - frustrated)
        conv1 = db.query(Conversation).filter(Conversation.customer_id == users[0].id).first()
        messages_data = [
            {
                "content": "Hola, necesito ayuda con mi pedido. Ha pasado más de una semana y todavía no he recibido nada.",
                "sender": "customer",
                "sentiment": "neutral",
                "score": 0.5,
                "label": "Neutral"
            },
            {
                "content": "Hello Maria! I understand you're waiting for your order. Let me check the status for you right away. Could you please provide your order number?",
                "sender": "ai",
                "sentiment": "positive",
                "score": 0.7,
                "label": "Helpful"
            },
            {
                "content": "El número de pedido es #ORD-2024-78542. Ya he preguntado TRES VECES y nadie me da una respuesta clara!!",
                "sender": "customer",
                "sentiment": "negative",
                "score": 0.78,
                "label": "Frustrated"
            },
            {
                "content": "I sincerely apologize for the frustration you've experienced, Maria. I can see your order #ORD-2024-78542 was shipped on December 5th but appears to be delayed at the local distribution center.",
                "sender": "ai",
                "sentiment": "positive",
                "score": 0.65,
                "label": "Apologetic"
            },
            {
                "content": "Esto es inaceptable! Necesito este paquete para un evento importante este fin de semana. Si no llega, voy a tener que cancelar todo!",
                "sender": "customer",
                "sentiment": "negative",
                "score": 0.92,
                "label": "Angry"
            },
        ]
        
        for i, msg_data in enumerate(messages_data):
            msg = Message(
                conversation_id=conv1.id,
                content=msg_data["content"],
                sender_type=msg_data["sender"],
                sender_name=users[0].name if msg_data["sender"] == "customer" else "AI Agent",
                sentiment=msg_data["sentiment"],
                sentiment_score=msg_data["score"],
                sentiment_label=msg_data["label"],
                is_escalation_trigger=msg_data["score"] > 0.8,
                created_at=datetime.utcnow() - timedelta(minutes=10-i*2)
            )
            db.add(msg)
        
        db.commit()
        print(f"[OK] Created {len(messages_data)} demo messages")
        
        print("")
        print("[SUCCESS] Database seeded successfully!")
        print("Run the server with: uvicorn app.main:app --reload")
        
    except Exception as e:
        print(f"[ERROR] Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
