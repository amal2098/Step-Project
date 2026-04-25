import 'package:flutter/material.dart';

import '../../../../data/repositories/auth_repository.dart';

class AuthViewModel extends ChangeNotifier {
  final AuthRepository _repository = AuthRepository();

  bool isLoading = false;
  bool acceptedPrivacy = false;

  Future<void> login(String email, String password) async {
    isLoading = true;
    notifyListeners();
    try {
      await _repository.login(email, password);
    } catch (_) {
      // API will be integrated with backend behavior later.
    } finally {
      isLoading = false;
      notifyListeners();
    }
  }

  Future<void> register(String fullName, String email, String phone, String password) async {
    isLoading = true;
    notifyListeners();
    try {
      await _repository.register(fullName, email, phone, password);
    } catch (_) {
      // API will be integrated with backend behavior later.
    } finally {
      isLoading = false;
      notifyListeners();
    }
  }

  void setPrivacy(bool value) {
    acceptedPrivacy = value;
    notifyListeners();
  }
}
