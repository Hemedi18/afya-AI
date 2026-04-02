import 'package:flutter/material.dart';

import '../../../core/theme/app_theme.dart';
import '../../../core/theme/theme_controller.dart';
import '../../../core/widgets/neo_widgets.dart';
import '../../auth/data/auth_api.dart';
import '../data/chat_api.dart';
import 'chat_messages_page.dart';

class ChatListPage extends StatefulWidget {
  const ChatListPage({super.key, required this.authApi});

  final AuthApi authApi;

  @override
  State<ChatListPage> createState() => _ChatListPageState();
}

class _ChatListPageState extends State<ChatListPage> {
  late final ChatApi _chatApi;
  bool _loading = true;
  String? _error;
  List<dynamic> _items = const [];

  @override
  void initState() {
    super.initState();
    _chatApi = ChatApi(widget.authApi.apiClient);
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final data = await _chatApi.getConversations();
      setState(() => _items = data);
    } catch (_) {
      setState(() => _error = 'Imeshindikana kupakia chats');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _logout() async {
    await widget.authApi.logout();
    if (!mounted) return;
    Navigator.of(context).popUntil((route) => route.isFirst);
  }

  Future<void> _openStartConversationDialog() async {
    final doctorCtrl = TextEditingController();
    final subjectCtrl = TextEditingController();
    final messageCtrl = TextEditingController();
    String? error;
    bool posting = false;

    await showDialog<void>(
      context: context,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (ctx, setLocal) {
            return AlertDialog(
              title: const Text('Anzisha private chat'),
              content: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    TextField(
                      controller: doctorCtrl,
                      decoration: const InputDecoration(labelText: 'Doctor username'),
                    ),
                    const SizedBox(height: 10),
                    TextField(
                      controller: subjectCtrl,
                      decoration: const InputDecoration(labelText: 'Mada (Subject)'),
                    ),
                    const SizedBox(height: 10),
                    TextField(
                      controller: messageCtrl,
                      minLines: 2,
                      maxLines: 4,
                      decoration: const InputDecoration(labelText: 'Ujumbe wa mwanzo'),
                    ),
                    if (error != null) ...[
                      const SizedBox(height: 8),
                      Text(error!, style: const TextStyle(color: AppTheme.danger, fontWeight: FontWeight.w600)),
                    ],
                  ],
                ),
              ),
              actions: [
                TextButton(
                  onPressed: posting ? null : () => Navigator.of(ctx).pop(),
                  child: const Text('Funga'),
                ),
                FilledButton(
                  onPressed: posting
                      ? null
                      : () async {
                          setLocal(() {
                            posting = true;
                            error = null;
                          });
                          try {
                            final convo = await _chatApi.startConversation(
                              doctorUsername: doctorCtrl.text.trim(),
                              subject: subjectCtrl.text.trim(),
                              openingMessage: messageCtrl.text.trim(),
                            );
                            if (!mounted || !ctx.mounted) return;
                            Navigator.of(ctx).pop();
                            await _load();
                            if (!mounted) return;
                            if (convo != null) {
                              final otherUser = (convo['other_user'] as Map?) ?? const {};
                              Navigator.of(context).push(
                                MaterialPageRoute(
                                  builder: (_) => ChatMessagesPage(
                                    chatApi: _chatApi,
                                    conversationId: convo['id'] as int,
                                    title: (otherUser['full_name'] ?? 'Chat').toString(),
                                    currentUserId: widget.authApi.currentUserId,
                                  ),
                                ),
                              );
                            }
                          } catch (e) {
                            setLocal(() {
                              posting = false;
                              error = e.toString().replaceFirst('Exception: ', '');
                            });
                          }
                        },
                  child: posting
                      ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Text('Tuma'),
                ),
              ],
            );
          },
        );
      },
    );

    doctorCtrl.dispose();
    subjectCtrl.dispose();
    messageCtrl.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: AppBackdrop(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(18, 14, 18, 20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Private chats', style: Theme.of(context).textTheme.headlineMedium?.copyWith(fontSize: 28)),
                        const SizedBox(height: 4),
                        const Text('Muonekano unaendana na web mobile. Ikiwa hakuna data bado, tumia + kuanza chat mpya.', style: TextStyle(color: AppTheme.muted)),
                      ],
                    ),
                  ),
                  IconButton(onPressed: _load, icon: const Icon(Icons.refresh_rounded)),
                  IconButton(onPressed: ThemeController.instance.toggle, icon: const Icon(Icons.brightness_6_outlined)),
                  IconButton(onPressed: _logout, icon: const Icon(Icons.logout_rounded)),
                ],
              ),
              const SizedBox(height: 16),
              Expanded(
                child: _loading
                    ? const Center(child: CircularProgressIndicator())
                    : _error != null
                        ? Center(child: Text(_error!))
                        : _items.isEmpty
                            ? Center(
                                child: NeoCard(
                                  child: Column(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      const Icon(Icons.forum_rounded, size: 52, color: AppTheme.primary),
                                      const SizedBox(height: 10),
                                      Text('Hakuna private chat bado', style: Theme.of(context).textTheme.titleMedium),
                                      const SizedBox(height: 6),
                                      const Text(
                                        'Bonyeza + kuanzisha chat mpya na doctor kwa username yake.',
                                        textAlign: TextAlign.center,
                                        style: TextStyle(color: AppTheme.muted),
                                      ),
                                      const SizedBox(height: 12),
                                      GradientButton(
                                        label: 'Anzisha chat',
                                        onPressed: _openStartConversationDialog,
                                        icon: const Icon(Icons.add_comment_rounded, color: Colors.white),
                                      ),
                                    ],
                                  ),
                                ),
                              )
                        : ListView.separated(
                            itemBuilder: (context, index) {
                              final item = _items[index] as Map<String, dynamic>;
                              final otherUser = (item['other_user'] as Map?) ?? const {};
                              final last = item['last_message'] as Map<String, dynamic>?;
                              final unread = (item['unread_count'] ?? 0) as int;
                              return NeoCard(
                                padding: const EdgeInsets.all(14),
                                child: InkWell(
                                  borderRadius: BorderRadius.circular(20),
                                  onTap: () {
                                    Navigator.of(context).push(
                                      MaterialPageRoute(
                                        builder: (_) => ChatMessagesPage(
                                          chatApi: _chatApi,
                                          conversationId: item['id'] as int,
                                          title: (otherUser['full_name'] ?? 'Chat').toString(),
                                          currentUserId: widget.authApi.currentUserId,
                                        ),
                                      ),
                                    );
                                  },
                                  child: Row(
                                    children: [
                                      Container(
                                        width: 52,
                                        height: 52,
                                        decoration: BoxDecoration(
                                          gradient: AppTheme.primaryGradient,
                                          borderRadius: BorderRadius.circular(18),
                                        ),
                                        child: Center(
                                          child: Text(
                                            ((otherUser['username'] ?? '?').toString()).substring(0, 1).toUpperCase(),
                                            style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800),
                                          ),
                                        ),
                                      ),
                                      const SizedBox(width: 12),
                                      Expanded(
                                        child: Column(
                                          crossAxisAlignment: CrossAxisAlignment.start,
                                          children: [
                                            Text((otherUser['full_name'] ?? 'User').toString(), style: Theme.of(context).textTheme.titleMedium),
                                            const SizedBox(height: 4),
                                            Text(
                                              (last?['content'] ?? item['subject'] ?? '').toString(),
                                              maxLines: 2,
                                              overflow: TextOverflow.ellipsis,
                                              style: const TextStyle(color: AppTheme.muted, height: 1.35),
                                            ),
                                          ],
                                        ),
                                      ),
                                      if (unread > 0)
                                        Container(
                                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                                          decoration: BoxDecoration(
                                            gradient: AppTheme.primaryGradient,
                                            borderRadius: BorderRadius.circular(999),
                                          ),
                                          child: Text('$unread', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800)),
                                        ),
                                    ],
                                  ),
                                ),
                              );
                            },
                            separatorBuilder: (_, _) => const SizedBox(height: 12),
                            itemCount: _items.length,
                          ),
              ),
            ],
          ),
        ),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _openStartConversationDialog,
        child: const Icon(Icons.add_rounded),
      ),
    );
  }
}
