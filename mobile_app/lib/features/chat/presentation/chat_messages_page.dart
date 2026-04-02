import 'dart:async';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/neo_widgets.dart';
import '../data/chat_api.dart';

class ChatMessagesPage extends StatefulWidget {
  const ChatMessagesPage({
    super.key,
    required this.chatApi,
    required this.conversationId,
    required this.title,
    this.currentUserId,
  });

  final ChatApi chatApi;
  final int conversationId;
  final String title;
  final int? currentUserId;

  @override
  State<ChatMessagesPage> createState() => _ChatMessagesPageState();
}

class _ChatMessagesPageState extends State<ChatMessagesPage> {
  final _textController = TextEditingController();
  List<dynamic> _messages = const [];
  bool _loading = true;
  bool _sending = false;
  int _lastId = 0;
  Timer? _pollTimer;
  String? _selectedFilePath;
  String? _selectedFileName;

  @override
  void initState() {
    super.initState();
    _load(initial: true);
    _startPolling();
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    _textController.dispose();
    super.dispose();
  }

  void _startPolling() {
    _pollTimer = Timer.periodic(const Duration(seconds: 2), (_) => _load());
  }

  Future<void> _load({bool initial = false}) async {
    try {
      final items = await widget.chatApi.getMessages(
        widget.conversationId,
        since: initial ? 0 : _lastId,
      );
      if (!mounted) return;
      setState(() {
        if (initial) {
          _messages = items;
        } else if (items.isNotEmpty) {
          _messages = [..._messages, ...items];
        }
        for (final msg in _messages) {
          if (msg is Map && msg['id'] is int) {
            final id = msg['id'] as int;
            if (id > _lastId) _lastId = id;
          }
        }
        _loading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _loading = false);
    }
  }

  Future<void> _send() async {
    final text = _textController.text.trim();
    final hasFile = _selectedFilePath != null && _selectedFilePath!.isNotEmpty;
    if ((text.isEmpty && !hasFile) || _sending) return;
    setState(() => _sending = true);
    try {
      final item = await widget.chatApi.sendMessage(
        widget.conversationId,
        text,
        filePath: _selectedFilePath,
        fileName: _selectedFileName,
      );
      _textController.clear();
      _selectedFilePath = null;
      _selectedFileName = null;
      if (item != null) {
        setState(() {
          _messages = [..._messages, item];
          if (item['id'] is int && (item['id'] as int) > _lastId) {
            _lastId = item['id'] as int;
          }
        });
      }
      await _load();
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  Future<void> _pickAttachment() async {
    final result = await FilePicker.platform.pickFiles(
      allowMultiple: false,
      type: FileType.custom,
      allowedExtensions: const [
        'jpg',
        'jpeg',
        'png',
        'gif',
        'webp',
        'mp4',
        'mov',
        'webm',
        'avi',
        'mkv',
        'pdf',
        'doc',
        'docx',
        'txt',
        'xls',
        'xlsx',
        'ppt',
        'pptx',
        'zip',
        'rar',
      ],
    );
    if (result == null || result.files.isEmpty) return;
    final file = result.files.first;
    if (file.path == null) return;
    setState(() {
      _selectedFilePath = file.path;
      _selectedFileName = file.name;
    });
  }

  Future<void> _openAttachment(String? rawUrl) async {
    if (rawUrl == null || rawUrl.isEmpty) return;
    final url = Uri.tryParse(rawUrl);
    if (url == null) return;
    await launchUrl(url, mode: LaunchMode.externalApplication);
  }

  bool _isImage(String name) {
    final n = name.toLowerCase();
    return n.endsWith('.jpg') || n.endsWith('.jpeg') || n.endsWith('.png') || n.endsWith('.gif') || n.endsWith('.webp');
  }

  bool _isVideo(String name) {
    final n = name.toLowerCase();
    return n.endsWith('.mp4') || n.endsWith('.mov') || n.endsWith('.webm') || n.endsWith('.avi') || n.endsWith('.mkv');
  }

  Widget _buildMessageBubble(Map<String, dynamic> item) {
    final senderId = item['sender_id'];
    final isMine = senderId is int && widget.currentUserId != null && senderId == widget.currentUserId;
    final hasAttachment = item['has_attachment'] == true;
    final attachmentName = (item['attachment_name'] ?? 'attachment').toString();
    final attachmentUrl = item['attachment_url']?.toString();
    final bool isImage = _isImage(attachmentName);
    final bool isVideo = _isVideo(attachmentName);

    return Align(
      alignment: isMine ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        constraints: const BoxConstraints(maxWidth: 310),
        margin: const EdgeInsets.symmetric(vertical: 6),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          gradient: isMine ? AppTheme.primaryGradient : null,
          color: isMine ? null : AppTheme.mobileSolid,
          borderRadius: BorderRadius.circular(22),
          border: Border.all(color: isMine ? Colors.transparent : AppTheme.mobileBorder),
          boxShadow: AppTheme.neoOuter,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (!isMine)
              Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Text(
                  (item['sender_name'] ?? 'User').toString(),
                  style: const TextStyle(fontWeight: FontWeight.w700, color: AppTheme.primary, fontSize: 12),
                ),
              ),
            Text(
              (item['content'] ?? '').toString().trim().isEmpty ? 'Attachment' : (item['content'] ?? '').toString(),
              style: TextStyle(color: isMine ? Colors.white : AppTheme.mobileText, height: 1.5),
            ),
            if (hasAttachment) ...[
              const SizedBox(height: 10),
              if (isImage || isVideo)
                InkWell(
                  onTap: () => _openAttachment(attachmentUrl),
                  borderRadius: BorderRadius.circular(18),
                  child: Container(
                    width: double.infinity,
                    constraints: const BoxConstraints(maxHeight: 270),
                    decoration: BoxDecoration(
                      color: isMine ? Colors.white.withValues(alpha: .14) : AppTheme.mobileInput,
                      borderRadius: BorderRadius.circular(18),
                      border: Border.all(color: isMine ? Colors.white24 : AppTheme.mobileBorder),
                    ),
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(18),
                      child: AspectRatio(
                        aspectRatio: 4 / 5,
                        child: Stack(
                          fit: StackFit.expand,
                          children: [
                            if (isImage)
                              Image.network(
                                attachmentUrl ?? '',
                                fit: BoxFit.contain,
                                errorBuilder: (context, error, stackTrace) => const Center(child: Icon(Icons.broken_image_outlined)),
                              )
                            else
                              Container(
                                color: Colors.black12,
                                child: const Center(
                                  child: Icon(Icons.play_circle_fill_rounded, size: 54, color: Colors.white),
                                ),
                              ),
                            Positioned(
                              left: 10,
                              top: 10,
                              child: Container(
                                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                                decoration: BoxDecoration(
                                  color: Colors.black.withValues(alpha: .54),
                                  borderRadius: BorderRadius.circular(999),
                                ),
                                child: Text(
                                  isImage ? 'Picha' : 'Video',
                                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700, fontSize: 12),
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                )
              else
                InkWell(
                  onTap: () => _openAttachment(attachmentUrl),
                  borderRadius: BorderRadius.circular(18),
                  child: Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: isMine ? Colors.white.withValues(alpha: .16) : AppTheme.mobileInput,
                      borderRadius: BorderRadius.circular(18),
                      border: Border.all(color: isMine ? Colors.white24 : AppTheme.mobileBorder),
                    ),
                    child: Row(
                      children: [
                        Container(
                          width: 42,
                          height: 42,
                          decoration: BoxDecoration(
                            color: isMine ? Colors.white.withValues(alpha: .16) : AppTheme.cardBg,
                            borderRadius: BorderRadius.circular(14),
                          ),
                          child: Icon(
                            Icons.attach_file_rounded,
                            color: isMine ? Colors.white : AppTheme.primary,
                          ),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            attachmentName,
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              color: isMine ? Colors.white : AppTheme.mobileText,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ),
                        Icon(Icons.open_in_new_rounded, color: isMine ? Colors.white : AppTheme.mobileText),
                      ],
                    ),
                  ),
                ),
            ],
            const SizedBox(height: 8),
            Align(
              alignment: Alignment.centerRight,
              child: Text(
                (item['created_at'] ?? '').toString(),
                style: TextStyle(color: isMine ? Colors.white70 : AppTheme.muted, fontSize: 11),
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: AppBackdrop(
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(18, 12, 18, 10),
              child: Row(
                children: [
                  IconButton(
                    onPressed: () => Navigator.of(context).maybePop(),
                    icon: const Icon(Icons.arrow_back_rounded),
                  ),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(widget.title, style: Theme.of(context).textTheme.titleLarge),
                        const SizedBox(height: 2),
                        const Text('Secure mobile chat • polling realtime', style: TextStyle(color: AppTheme.muted, fontSize: 12)),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            Expanded(
              child: _loading
                  ? const Center(child: CircularProgressIndicator())
                  : ListView.builder(
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                      itemCount: _messages.length,
                      itemBuilder: (context, index) => _buildMessageBubble(_messages[index] as Map<String, dynamic>),
                    ),
            ),
            if (_selectedFilePath != null)
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
                child: NeoCard(
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                  child: Row(
                    children: [
                      const Icon(Icons.attach_file_rounded, color: AppTheme.primary),
                      const SizedBox(width: 8),
                      Expanded(child: Text('Selected: ${_selectedFileName ?? 'attachment'}', maxLines: 2, overflow: TextOverflow.ellipsis)),
                      IconButton(
                        onPressed: () {
                          setState(() {
                            _selectedFilePath = null;
                            _selectedFileName = null;
                          });
                        },
                        icon: const Icon(Icons.close_rounded),
                      ),
                    ],
                  ),
                ),
              ),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 14),
              child: NeoCard(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                child: Row(
                  children: [
                    IconButton(
                      onPressed: _sending ? null : _pickAttachment,
                      icon: const Icon(Icons.attach_file_rounded),
                    ),
                    Expanded(
                      child: TextField(
                        controller: _textController,
                        minLines: 1,
                        maxLines: 4,
                        decoration: const InputDecoration(
                          hintText: 'Andika ujumbe...',
                          border: InputBorder.none,
                          enabledBorder: InputBorder.none,
                          focusedBorder: InputBorder.none,
                          filled: false,
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    GestureDetector(
                      onTap: _sending ? null : _send,
                      child: Container(
                        width: 46,
                        height: 46,
                        decoration: BoxDecoration(
                          gradient: AppTheme.primaryGradient,
                          borderRadius: BorderRadius.circular(18),
                        ),
                        child: _sending
                            ? const Padding(
                                padding: EdgeInsets.all(12),
                                child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                              )
                            : const Icon(Icons.send_rounded, color: Colors.white),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
