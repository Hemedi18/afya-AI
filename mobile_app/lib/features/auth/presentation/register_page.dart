import 'package:flutter/material.dart';

import '../../../core/theme/app_theme.dart';
import '../../../core/theme/theme_controller.dart';
import '../../../core/widgets/neo_widgets.dart';
import '../data/auth_api.dart';
import '../../home/presentation/home_shell_page.dart';

class RegisterPage extends StatefulWidget {
  const RegisterPage({super.key, required this.authApi});

  final AuthApi authApi;

  @override
  State<RegisterPage> createState() => _RegisterPageState();
}

class _RegisterPageState extends State<RegisterPage> {
  final _formKey = GlobalKey<FormState>();
  final _usernameController = TextEditingController();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _loading = false;
  String? _error;

  @override
  void dispose() {
    _usernameController.dispose();
    _emailController.dispose();
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
      await widget.authApi.register(
        username: _usernameController.text.trim(),
        email: _emailController.text.trim(),
        password: _passwordController.text,
      );
      if (!mounted) return;
      Navigator.of(context).pushAndRemoveUntil(
        MaterialPageRoute(builder: (_) => HomeShellPage(authApi: widget.authApi)),
        (route) => false,
      );
    } catch (e) {
      if (!mounted) return;
      final message = e.toString().replaceFirst('Exception: ', '');
      setState(() => _error = message);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: AppBackdrop(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(18, 14, 18, 24),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                IconButton(
                  onPressed: () => Navigator.of(context).maybePop(),
                  icon: const Icon(Icons.arrow_back_rounded),
                ),
                Align(
                  alignment: Alignment.centerRight,
                  child: IconButton(
                    onPressed: ThemeController.instance.toggle,
                    icon: const Icon(Icons.brightness_6_outlined),
                  ),
                ),
                const SizedBox(height: 4),
                const SectionTitle(
                  title: 'Tengeneza account',
                  subtitle: 'Muundo huu unaiga visual language ya small devices kwenye web yako ili flow ifanane kila platform.',
                ),
                const SizedBox(height: 18),
                NeoCard(
                  child: Column(
                    children: [
                      TextFormField(
                        controller: _usernameController,
                        decoration: const InputDecoration(labelText: 'Username'),
                        validator: (v) => (v == null || v.trim().isEmpty) ? 'Weka username' : null,
                      ),
                      const SizedBox(height: 10),
                      TextFormField(
                        controller: _emailController,
                        decoration: const InputDecoration(labelText: 'Email (optional)'),
                      ),
                      const SizedBox(height: 10),
                      TextFormField(
                        controller: _passwordController,
                        decoration: const InputDecoration(labelText: 'Password'),
                        obscureText: true,
                        validator: (v) {
                          if (v == null || v.isEmpty) return 'Weka password';
                          if (v.length < 6) return 'Password lazima iwe angalau herufi 6';
                          return null;
                        },
                      ),
                      const SizedBox(height: 14),
                      if (_error != null)
                        Padding(
                          padding: const EdgeInsets.only(bottom: 12),
                          child: Text(_error!, style: const TextStyle(color: AppTheme.danger, fontWeight: FontWeight.w600)),
                        ),
                      GradientButton(
                        label: 'Fungua account',
                        onPressed: _loading ? null : _submit,
                        busy: _loading,
                        icon: const Icon(Icons.person_add_alt_1_rounded, color: Colors.white),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
