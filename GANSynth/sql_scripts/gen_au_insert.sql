INSERT INTO gansynth.gen_au
(id, dur, chat_id, genre_id, gen_num, aud_link, usr_mark, created_at)
VALUES (%s, %s, (SELECT id FROM gansynth.chats WHERE user_id=%s), %s, %s, NULL, NULL, %s);