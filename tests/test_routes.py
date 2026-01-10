from app.models import CourseRegistration


def test_public_index(client):
    resp = client.get('/')
    assert resp.status_code == 200


def test_about_page(client):
    resp = client.get('/about-kontakt')
    assert resp.status_code == 200
    assert b'About' in resp.data


def test_course_listing(client, course):
    resp = client.get('/angebot/')
    assert resp.status_code == 200
    assert b'Testkurs' in resp.data


def test_course_registration_flow(client, course):
    resp = client.post(
        f'/angebot/{course.id}/register',
        data={
            'vorname': 'Max',
            'name': 'Muster',
            'telefonnummer': '123456',
            'email': 'test@example.com',
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    with client.application.app_context():
        assert CourseRegistration.query.count() == 1
