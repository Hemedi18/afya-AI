import 'package:flutter/material.dart';

import 'core/network/api_client.dart';
import 'core/storage/token_storage.dart';
import 'core/theme/app_theme.dart';
import 'core/theme/theme_controller.dart';
import 'features/auth/data/auth_api.dart';
import 'features/auth/presentation/login_page.dart';
import 'features/home/presentation/home_shell_page.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const AfyaAiApp());
}

class AfyaAiApp extends StatefulWidget {
  const AfyaAiApp({super.key});

  @override
  State<AfyaAiApp> createState() => _AfyaAiAppState();
}

class _AfyaAiAppState extends State<AfyaAiApp> {
  late final TokenStorage _tokenStorage;
  late final ApiClient _apiClient;
  late final AuthApi _authApi;
  bool _checkingSession = true;
  bool _hasSession = false;

  @override
  void initState() {
    super.initState();
    _tokenStorage = TokenStorage();
    _apiClient = ApiClient(_tokenStorage);
    _authApi = AuthApi(_apiClient, _tokenStorage);
    _bootstrap();
  }

  Future<void> _bootstrap() async {
    final hasSession = await _authApi.hydrateSession();
    if (!mounted) return;
    setState(() {
      _hasSession = hasSession;
      _checkingSession = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder<ThemeMode>(
      valueListenable: ThemeController.instance.mode,
      builder: (context, mode, _) {
        return MaterialApp(
          debugShowCheckedModeBanner: false,
          title: 'Afya AI Mobile',
          theme: AppTheme.theme(),
          darkTheme: AppTheme.darkTheme(),
          themeMode: mode,
          home: _checkingSession
              ? const Scaffold(body: Center(child: CircularProgressIndicator()))
              : _hasSession
                  ? HomeShellPage(authApi: _authApi)
                  : LoginPage(authApi: _authApi),
        );
      },
    );
  }
}
