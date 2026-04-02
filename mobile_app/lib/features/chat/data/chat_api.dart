import 'package:dio/dio.dart';

import '../../../core/network/api_client.dart';

class ChatApi {
  ChatApi(this._apiClient);

  final ApiClient _apiClient;

  Future<List<dynamic>> getConversations() async {
    final res = await _apiClient.dio.get('/chats/');
    final data = res.data;
    if (data is Map && data['ok'] == true && data['items'] is List) {
      return data['items'] as List<dynamic>;
    }
    return const [];
  }

  Future<Map<String, dynamic>?> startConversation({
    required String doctorUsername,
    required String subject,
    required String openingMessage,
  }) async {
    final res = await _apiClient.dio.post(
      '/chats/start/',
      data: {
        'doctor_username': doctorUsername,
        'subject': subject,
        'opening_message': openingMessage,
      },
    );
    final data = res.data;
    if (data is Map && data['ok'] == true && data['conversation'] is Map<String, dynamic>) {
      return data['conversation'] as Map<String, dynamic>;
    }
    return null;
  }

  Future<List<dynamic>> getMessages(int conversationId, {int since = 0}) async {
    final res = await _apiClient.dio.get('/chats/$conversationId/', queryParameters: {'since': since});
    final data = res.data;
    if (data is Map && data['ok'] == true && data['items'] is List) {
      return data['items'] as List<dynamic>;
    }
    return const [];
  }

  Future<Map<String, dynamic>?> sendMessage(
    int conversationId,
    String content, {
    String? filePath,
    String? fileName,
  }) async {
    final bool hasFile = filePath != null && filePath.isNotEmpty;
    final payload = hasFile
        ? FormData.fromMap(
            {
              'content': content,
              'attachment': await MultipartFile.fromFile(filePath, filename: fileName),
            },
          )
        : {'content': content};

    final res = await _apiClient.dio.post('/chats/$conversationId/', data: payload);
    final data = res.data;
    if (data is Map && data['ok'] == true && data['item'] is Map<String, dynamic>) {
      return data['item'] as Map<String, dynamic>;
    }
    return null;
  }
}
