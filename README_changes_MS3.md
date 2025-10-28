# 📆 NewsJuice (AC215 - Milestone 3)


## 👥 Team

- **Khaled Aly**  
- **Zac Sardi-Santos**  
- **Joshua Rosenblum**  
- **Christian Michel**

**Team name:** `NewsJuice`

---

## 📚 Overview of changes versus Milestone 2


- Added fine tuning pipeline Using a teacher/student approach. Since the largest cost in this project is the LLM call costs, we are attempting to finetune a smaller model such as Qwen 0.6b to generate the podcasts by learning from the bigger model (Gemini)
- Added 8 more scrapers, completing the scrapers for Harvard News Sources.
- Added chatter_deployed and frontend_deployed services in "Services" folder (first version of all with frontend and fully deployed with Cloud Run), accessible: at *www.newsjuiceapp.com*). See README files inside the folder

