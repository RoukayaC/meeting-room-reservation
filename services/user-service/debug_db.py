from app import create_app
from app.models import User

app = create_app()

def check_database():
    """Debug utility to check database contents"""
    with app.app_context():
        users = User.query.all()
        print(f"Total users in database: {len(users)}")
        for user in users:
            print(f"ID: {user.id}, Email: {user.email}, Role: {user.role}")

if __name__ == "__main__":
    check_database()