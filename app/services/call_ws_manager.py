from uuid import UUID

from fastapi import WebSocket


class CallWSManager:
    def __init__(self) -> None:
        self.active_connections: dict[UUID, WebSocket] = {}
        self.users_in_call: set[UUID] = set()

    async def connect(self, user_id: UUID, websocket: WebSocket) -> None:
        await websocket.accept()

        old_websocket = self.active_connections.get(user_id)
        self.active_connections[user_id] = websocket

        print(f'[CALL_WS] connected user={user_id}')

        if old_websocket is not None and old_websocket is not websocket:
            try:
                await old_websocket.close()
                print(f'[CALL_WS] closed previous socket for user={user_id}')
            except Exception as e:
                print(f'[CALL_WS] failed to close previous socket for user={user_id}: {e}')

    def disconnect(self, user_id: UUID, websocket: WebSocket | None = None) -> None:
        current_websocket = self.active_connections.get(user_id)

        if websocket is not None and current_websocket is not websocket:
            print(f'[CALL_WS] ignore disconnect of stale socket for user={user_id}')
            return

        self.active_connections.pop(user_id, None)
        self.users_in_call.discard(user_id)
        print(f'[CALL_WS] disconnected user={user_id}')

    def is_online(self, user_id: UUID) -> bool:
        return user_id in self.active_connections

    def is_in_call(self, user_id: UUID) -> bool:
        return user_id in self.users_in_call

    def start_call(self, user_id: UUID) -> None:
        self.users_in_call.add(user_id)
        print(f'[CALL_WS] start_call user={user_id}')

    def end_call(self, user_id: UUID) -> None:
        self.users_in_call.discard(user_id)
        print(f'[CALL_WS] end_call user={user_id}')

    async def send_to_user(self, user_id: UUID, message: dict) -> bool:
        websocket = self.active_connections.get(user_id)
        if websocket is None:
            print(
                f'[CALL_WS] send_to_user failed: '
                f'user={user_id}, reason=no_active_connection, type={message.get("type")}'
            )
            return False

        try:
            await websocket.send_json(message)
            print(
                f'[CALL_WS] sent: '
                f'user={user_id}, type={message.get("type")}, call_id={message.get("call_id")}'
            )
            return True
        except Exception as e:
            print(
                f'[CALL_WS] send_to_user exception: '
                f'user={user_id}, type={message.get("type")}, '
                f'call_id={message.get("call_id")}, error={e}'
            )
            self.disconnect(user_id, websocket)
            return False


call_ws_manager = CallWSManager()