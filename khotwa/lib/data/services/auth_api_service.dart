import 'package:dio/dio.dart';

import '../../core/constants/api_constants.dart';
import '../../core/network/api_client.dart';

class AuthApiService {
  final ApiClient _client;

  AuthApiService(this._client);

  Future<Response<dynamic>> login({required String email, required String password}) {
    return _client.dio.post(ApiConstants.login, data: {'email': email, 'password': password});
  }

  Future<Response<dynamic>> register({
    required String fullName,
    required String email,
    required String phone,
    required String password,
  }) {
    return _client.dio.post(
      ApiConstants.register,
      data: {'full_name': fullName, 'email': email, 'phone': phone, 'password': password},
    );
  }
}
