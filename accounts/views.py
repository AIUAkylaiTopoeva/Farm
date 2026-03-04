from rest_framework import generics, permissions
from rest_framework.response import Response

from .serializers import RegisterSerializer, MeSerializer


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class MeView(generics.GenericAPIView):
    serializer_class = MeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        return Response(self.get_serializer(request.user).data)