import 'package:dio/dio.dart';

import '../../../core/network/api_client.dart';
import '../../../core/storage/token_storage.dart';

class AuthApi {
  AuthApi(this._apiClient, this._tokenStorage);

  final ApiClient _apiClient;
  final TokenStorage _tokenStorage;
  int? currentUserId;
  String? currentUsername;

  ApiClient get apiClient => _apiClient;

  String _extractError(Object error, {String fallback = 'Request failed'}) {
    if (error is DioException) {
      final data = error.response?.data;
      if (data is Map && data['error'] != null) {
        return data['error'].toString();
      }
      if (error.type == DioExceptionType.connectionError || error.type == DioExceptionType.connectionTimeout) {
        return 'Imeshindikana kuunganisha server. Hakikisha Django server inawaka na IP ni sahihi.';
      }
    }
    return fallback;
  }

  void _hydrateUser(Map<dynamic, dynamic> data) {
    final user = data['user'];
    if (user is Map) {
      currentUserId = user['id'] is int ? user['id'] as int : int.tryParse('${user['id']}');
      currentUsername = user['username']?.toString();
    }
  }

  Future<void> register({
    required String username,
    required String password,
    String email = '',
    String firstName = '',
    String lastName = '',
  }) async {
    try {
      final res = await _apiClient.dio.post(
        '/auth/register/',
        data: {
          'username': username,
          'password': password,
          'email': email,
          'first_name': firstName,
          'last_name': lastName,
        },
      );

      final data = res.data;
      if (data is! Map || data['ok'] != true || data['token'] == null) {
        throw Exception('Register failed');
      }
      await _tokenStorage.saveToken(data['token'].toString());
      _hydrateUser(data);
    } catch (e) {
      throw Exception(_extractError(e, fallback: 'Usajili umeshindikana.'));
    }
  }

  Future<void> login({required String username, required String password}) async {
    try {
      final res = await _apiClient.dio.post(
        '/auth/login/',
        data: {'username': username, 'password': password},
      );

      final data = res.data;
      if (data is! Map || data['ok'] != true || data['token'] == null) {
        throw Exception('Login failed');
      }

      await _tokenStorage.saveToken(data['token'].toString());
      _hydrateUser(data);
    } catch (e) {
      throw Exception(_extractError(e, fallback: 'Login imeshindikana.'));
    }
  }

  Future<void> logout() async {
    try {
      await _apiClient.dio.post('/auth/logout/');
    } on DioException {
      // ignore API error on logout and clear local token anyway
    }
    await _tokenStorage.clearToken();
    currentUserId = null;
    currentUsername = null;
  }

  Future<bool> hydrateSession() async {
    final token = await _tokenStorage.getToken();
    if (token == null || token.isEmpty) return false;
    try {
      final res = await _apiClient.dio.get('/auth/me/');
      final data = res.data;
      if (data is Map && data['ok'] == true) {
        _hydrateUser(data);
        return true;
      }
    } on DioException {
      await _tokenStorage.clearToken();
    }
    return false;
  }
}
