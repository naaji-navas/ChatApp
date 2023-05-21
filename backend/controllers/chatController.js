const asyncHandler = require('express-async-handler')

const accesChat=asyncHandler(async(req,res)=>{
  const {id}=req.params
  const chat=await Chat.findById(id)
  if(chat){
    res.json(chat)
  }else{
    res.status(404)
    throw new Error('Chat Not Found')
  }
}