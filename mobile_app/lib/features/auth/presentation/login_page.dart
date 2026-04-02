import 'package:flutter/material.dart';

import '../../../core/theme/app_theme.dart';
import '../../../core/theme/theme_controller.dart';
import '../../../core/widgets/neo_widgets.dart';
import '../data/auth_api.dart';
import '../../home/presentation/home_shell_page.dart';
import 'register_page.dart';

class LoginPage extends StatefulWidget {
  const LoginPage({super.key, required this.authApi});

  final AuthApi authApi;

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final _formKey = GlobalKey<FormState>();
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _loading = false;
  String? _error;

  @override
  void dispose() {
    _usernameController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      await widget.authApi.login(
        username: _usernameController.text.trim(),
        password: _passwordController.text,
      );
      if (!mounted) return;
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(
          builder: (_) => HomeShellPage(authApi: widget.authApi),
        ),
      );
    } catch (e) {
      final message = e.toString().replaceFirst('Exception: ', '');
      setState(() => _error = message);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final screenHeight = MediaQuery.of(context).size.height;
    final viewPadding = MediaQuery.of(context).viewPadding.top;
    final availableHeight = screenHeight - viewPadding - 24; // Account for bottom padding
    
    return Scaffold(
      body: AppBackdrop(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(18, 14, 18, 24),
          child: ConstrainedBox(
            constraints: BoxConstraints(minHeight: availableHeight),
            child: Form(
              key: _formKey,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const SizedBox(height: 18),
                  Align(
                    alignment: Alignment.centerRight,
                    child: IconButton(
                      onPressed: ThemeController.instance.toggle,
                      icon: const Icon(Icons.brightness_6_outlined),
                    ),
                  ),
                  const SectionTitle(
                    title: 'Afya AI',
                    subtitle: 'Muonekano wa app unaendana na mobile theme ya web yako ili user apate uzoefu uleule kila mahali.',
                  ),
                  const SizedBox(height: 18),
                  NeoCard(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Container(
                          width: 58,
                          height: 58,
                          decoration: BoxDecoration(
                            gradient: AppTheme.primaryGradient,
                            borderRadius: BorderRadius.circular(18),
                            boxShadow: [
                              BoxShadow(
                                color: AppTheme.primary.withValues(alpha: .28),
                                blurRadius: 20,
                                offset: const Offset(0, 10),
                              ),
                            ],
                          ),
                          child: const Icon(Icons.health_and_safety_rounded, color: Colors.white, size: 28),
                        ),
                        const SizedBox(height: 16),
                        Text('Karibu tena', style: Theme.of(context).textTheme.titleLarge),
                        const SizedBox(height: 6),
                        const Text('Ingia kwa usalama, token zako zinahifadhiwa kwenye secure storage ya simu.'),
                        const SizedBox(height: 16),
                        TextFormField(
                          controller: _usernameController,
                          decoration: const InputDecoration(labelText: 'Username'),
                          validator: (v) => (v == null || v.trim().isEmpty) ? 'Weka username' : null,
                        ),
                        const SizedBox(height: 12),
                        TextFormField(
                          controller: _passwordController,
                          decoration: const InputDecoration(labelText: 'Password'),
                          obscureText: true,
                          validator: (v) => (v == null || v.isEmpty) ? 'Weka password' : null,
                        ),
                        const SizedBox(height: 14),
                        if (_error != null)
                          Padding(
                            padding: const EdgeInsets.only(bottom: 12),
                            child: Text(_error!, style: const TextStyle(color: AppTheme.danger, fontWeight: FontWeight.w600)),
                          ),
                        GradientButton(
                          label: 'Ingia',
                          onPressed: _loading ? null : _submit,
                          busy: _loading,
                          icon: const Icon(Icons.lock_open_rounded, color: Colors.white),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),
                  Center(
                    child: TextButton(
                      onPressed: _loading
                          ? null
                          : () {
                              Navigator.of(context).push(
                                MaterialPageRoute(
                                  builder: (_) => RegisterPage(authApi: widget.authApi),
                                ),
                              );
                            },
                      child: const Text('Huna account? Register'),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
