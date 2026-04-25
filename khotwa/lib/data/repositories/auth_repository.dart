import '../../core/network/api_client.dart';
import '../services/auth_api_service.dart';

class AuthRepository {
  final AuthApiService _authApiService = AuthApiService(ApiClient());

  Future<void> login(String email, String password) async {
    await _authApiService.login(email: email, password: password);
  }

  Future<void> register(String fullName, String email, String phone, String password) async {
    await _authApiService.register(
      fullName: fullName,
      email: email,
      phone: phone,
      password: password,
    );
  }
}
