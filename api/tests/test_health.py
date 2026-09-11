from fastapi.testclient import TestClient


def test_health_responde_ok(client: TestClient) -> None:
    respuesta = client.get("/api/health")

    assert respuesta.status_code == 200
    assert respuesta.json()["status"] == "ok"


def test_health_no_toca_la_base(client: TestClient) -> None:
    """
    /api/health tiene que contestar aunque la base no responda.

    Es lo que mira el HEALTHCHECK de la imagen: si consultara la base, un
    parpadeo de Postgres reiniciaria un proceso perfectamente sano. La
    comprobacion de la base vive en /api/ready, que llega mas adelante.

    Aqui se rompe el engine a proposito y se exige que siga en 200.
    """
    import app.db.session as sesion_db

    original = sesion_db.engine
    sesion_db.engine = None  # type: ignore[assignment]
    try:
        assert client.get("/api/health").status_code == 200
    finally:
        sesion_db.engine = original
