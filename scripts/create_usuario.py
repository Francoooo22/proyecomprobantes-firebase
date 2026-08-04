"""Crea un usuario en Firebase Auth y su perfil en Firestore (rol vendedor/supervisor).

Uso:
    python3 scripts/create_usuario.py --email vendedor@grupo.com --password "123456" --nombre "Juan" --rol supervisor --sucursal "Lantier"

Requiere:
    - FIREBASE_SA_PATH apuntando al JSON de service account (o se pasa con --sa)
    - FIREBASE_PROJECT_ID
"""

import argparse
import os

import firebase_admin
from firebase_admin import auth, credentials
from google.auth.transport.requests import AuthorizedSession
from google.cloud import firestore as gcfirestore
from google.oauth2.service_account import Credentials

ROLES = {"vendedor", "supervisor"}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--email", required=True)
    p.add_argument("--password", required=True)
    p.add_argument("--nombre", required=True)
    p.add_argument("--rol", required=True, choices=sorted(ROLES))
    p.add_argument("--sucursal", default="")
    p.add_argument("--database", default="(default)", help="Id de la base Firestore")
    p.add_argument("--sa", default=os.environ.get("FIREBASE_SA_PATH"), help="Ruta al service account JSON")
    args = p.parse_args()

    if not args.sa or not os.path.exists(args.sa):
        raise SystemExit("Falta el service account: pasá --sa o FIREBASE_SA_PATH")

    firebase_admin.initialize_app(credentials.Certificate(args.sa))

    sa_credentials = Credentials.from_service_account_file(
        args.sa,
        scopes=["https://www.googleapis.com/auth/cloud-platform", "https://www.googleapis.com/auth/datastore"],
    )
    db = gcfirestore.Client(project=sa_credentials.project_id, credentials=sa_credentials, database=args.database)

    try:
        user = auth.get_user_by_email(args.email)
        print(f"Usuario existente, actualizo (uid {user.uid})")
    except firebase_admin.auth.UserNotFoundError:
        user = auth.create_user(email=args.email, password=args.password, display_name=args.nombre)
        print(f"Usuario creado (uid {user.uid})")

    db.collection("usuarios").document(user.uid).set({
        "email": args.email,
        "nombre": args.nombre,
        "rol": args.rol,
        "sucursal": args.sucursal,
        "creado": gcfirestore.SERVER_TIMESTAMP,
    })
    print(f"OK {args.email} rol {args.rol} en db '{args.database}'")


if __name__ == "__main__":
    main()
