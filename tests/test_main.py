from fastapi import status


class TestMain:
    def test_health_success(self, request):
        client = request.instance.client

        response = client.get(f"/health")

        expected_response = "ok"
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == expected_response
