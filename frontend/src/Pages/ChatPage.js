import React, {useEffect, useState} from "react";
import axios from "axios";

const ChatPage = () => {
  //useState for chats
  const [chats, setChats] = useState([]);





  useEffect(() => {
    fetchChats().then(r => console.log(r));

  }, []);
  const fetchChats = async () => {
    const { data } = await axios.get("/api/chats");

    setChats(data)
  };

  return <div>
    <h1>Chat Page</h1>
    <ul>
      {chats.map(chat => (
        <li key={chat._id}>{chat.chatName}</li>
      ))}
    </ul>

  </div>;
};
export default ChatPage;
