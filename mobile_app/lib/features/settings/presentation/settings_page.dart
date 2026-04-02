import 'package:flutter/material.dart';

import '../../../core/theme/app_theme.dart';
import '../../../core/theme/theme_controller.dart';
import '../../../core/widgets/neo_widgets.dart';
import '../../auth/data/auth_api.dart';

class SettingsPage extends StatelessWidget {
  const SettingsPage({super.key, required this.authApi, required this.onLoggedOut});

  final AuthApi authApi;
  final VoidCallback onLoggedOut;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: AppBackdrop(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(18, 14, 18, 20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Settings', style: Theme.of(context).textTheme.headlineMedium?.copyWith(fontSize: 28)),
              const SizedBox(height: 8),
              const Text('Theme na usalama wa app ya simu.', style: TextStyle(color: AppTheme.muted)),
              const SizedBox(height: 16),
              NeoCard(
                child: Column(
                  children: [
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      leading: const Icon(Icons.palette_outlined),
                      title: const Text('Badili theme'),
                      subtitle: const Text('Light / Dark'),
                      trailing: IconButton(
                        onPressed: ThemeController.instance.toggle,
                        icon: const Icon(Icons.brightness_6_outlined),
                      ),
                    ),
                    const Divider(),
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      leading: const Icon(Icons.logout_rounded),
                      title: const Text('Logout'),
                      onTap: () async {
                        await authApi.logout();
                        onLoggedOut();
                      },
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
