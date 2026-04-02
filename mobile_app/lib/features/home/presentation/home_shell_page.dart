import 'package:flutter/material.dart';

import '../../../core/theme/theme_controller.dart';
import '../../auth/data/auth_api.dart';
import '../../chat/presentation/chat_list_page.dart';
import '../../settings/presentation/settings_page.dart';

class HomeShellPage extends StatefulWidget {
  const HomeShellPage({super.key, required this.authApi});

  final AuthApi authApi;

  @override
  State<HomeShellPage> createState() => _HomeShellPageState();
}

class _HomeShellPageState extends State<HomeShellPage> {
  int _index = 0;

  @override
  Widget build(BuildContext context) {
    final pages = [
      ChatListPage(authApi: widget.authApi),
      SettingsPage(
        authApi: widget.authApi,
        onLoggedOut: () {
          if (!mounted) return;
          Navigator.of(context).popUntil((route) => route.isFirst);
        },
      ),
    ];

    return Scaffold(
      body: pages[_index],
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (v) => setState(() => _index = v),
        destinations: [
          const NavigationDestination(icon: Icon(Icons.chat_bubble_outline_rounded), label: 'Chats'),
          NavigationDestination(
            icon: const Icon(Icons.settings_outlined),
            selectedIcon: const Icon(Icons.settings_rounded),
            label: ThemeController.instance.mode.value == ThemeMode.dark ? 'Settings • Dark' : 'Settings • Light',
          ),
        ],
      ),
    );
  }
}
